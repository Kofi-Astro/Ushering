"""Login, session, and password-reset handling for the admin panel.
There's still exactly one admin account (see ADMIN_USERNAME/
ADMIN_PASSWORD in app/config.py) — this isn't a real multi-user auth
system — but the password itself can now live in two possible places:

  - The environment variable ADMIN_PASSWORD, exactly as before. This is
    still the only thing that matters on a fresh install.
  - A hashed password stored in the admin_auth database row, which takes
    over completely the moment it's ever set — see check_credentials
    below. This exists so "I forgot the password" has a real self-service
    answer (a reset-link email) without the running app needing to
    rewrite its own environment variables, which it has no way to do.

Also unchanged from before:
  - Credentials are compared with hmac.compare_digest (constant-time, so
    a timing attack can't be used to guess a value character by
    character) — both the username comparison and whichever password
    comparison applies always run, rather than short-circuiting on the
    first mismatch, for the same reason.
  - The "session" is a signed, timestamped token (via itsdangerous) baked
    straight into a cookie — there's no server-side session store to look
    up. The cookie IS the session; it can't be forged without knowing
    SECRET_KEY, and it self-expires after SESSION_MAX_AGE.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from fastapi import Cookie, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from .config import get_settings
from .models import AdminAuth

settings = get_settings()
SESSION_COOKIE = "admin_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours
RESET_TOKEN_MAX_AGE = timedelta(hours=1)
_PBKDF2_ITERATIONS = 200_000


def _serializer() -> URLSafeTimedSerializer:
    """itsdangerous serializer used to both create and verify session
    tokens. `salt` namespaces this specific use of SECRET_KEY, so a token
    made for one purpose can't accidentally be replayed for another if
    the same secret key is ever reused elsewhere."""
    return URLSafeTimedSerializer(settings.secret_key, salt="admin-session")


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 via the standard library — no bcrypt/passlib
    dependency, which would be overkill for a single account that isn't a
    realistic offline-brute-force target. Stored as "<salt hex>$<hash
    hex>" so verify_password doesn't need the salt passed in separately."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(actual, expected)


def check_credentials(username: str, password: str, db: Session) -> bool:
    """Compares the submitted login form against the one configured admin
    account. If a password has ever been set via the reset flow
    (admin_auth.password_hash), that takes over completely — the
    ADMIN_PASSWORD env var is no longer checked at all for this account
    once that happens. Both the username and whichever password check
    applies always run (never short-circuited), so a wrong username can't
    be distinguished from a wrong password by response timing."""
    valid_user = hmac.compare_digest(username, settings.admin_username)

    admin_auth = db.query(AdminAuth).filter(AdminAuth.id == 1).first()
    if admin_auth and admin_auth.password_hash:
        valid_pass = verify_password(password, admin_auth.password_hash)
    else:
        valid_pass = hmac.compare_digest(password, settings.admin_password)

    return valid_user and valid_pass


def create_reset_token(db: Session) -> str:
    """Generates a fresh, single-use reset token, valid for
    RESET_TOKEN_MAX_AGE, and saves it to the admin_auth row (creating that
    row if this is the very first password-related action ever taken).
    Returns the raw token to embed in the emailed reset link."""
    admin_auth = db.query(AdminAuth).filter(AdminAuth.id == 1).first()
    if not admin_auth:
        admin_auth = AdminAuth(id=1)
        db.add(admin_auth)

    token = secrets.token_urlsafe(32)
    admin_auth.reset_token = token
    admin_auth.reset_token_expires = datetime.utcnow() + RESET_TOKEN_MAX_AGE
    db.commit()
    return token


def verify_reset_token(token: str, db: Session) -> AdminAuth | None:
    """Returns the admin_auth row if `token` matches its stored
    reset_token and hasn't expired, else None. Used by both the GET (show
    the "set a new password" form, or don't) and POST (actually apply it)
    sides of /reset-password/{token}."""
    admin_auth = db.query(AdminAuth).filter(AdminAuth.id == 1).first()
    if not admin_auth or not admin_auth.reset_token or not admin_auth.reset_token_expires:
        return None
    if not hmac.compare_digest(admin_auth.reset_token, token):
        return None
    if datetime.utcnow() > admin_auth.reset_token_expires:
        return None
    return admin_auth


def create_session_token() -> str:
    """Called on successful login (see app/admin/routers/auth.py) to
    produce the value stored in the admin_session cookie."""
    return _serializer().dumps({"user": settings.admin_username})


def verify_session_token(token: str | None) -> bool:
    """Checks a session cookie's value is both correctly signed (proving
    it was issued by create_session_token, not forged) and not older than
    SESSION_MAX_AGE. Used directly by require_admin below."""
    if not token:
        return False
    try:
        _serializer().loads(token, max_age=SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_admin(admin_session: str | None = Cookie(default=None)) -> None:
    """FastAPI dependency guarding every admin route — add
    `Depends(require_admin)` (or a router-level `dependencies=[...]`, as
    every router under app/admin/routers/ does) to any route that should
    require login. Raising a redirect as an HTTPException (rather than
    returning a bool the route has to check) keeps every protected route
    handler focused on its own job instead of repeating an auth check."""
    if not verify_session_token(admin_session):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
