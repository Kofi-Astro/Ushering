"""Login + session handling for the admin panel. There's no user table and
no password hashing library here on purpose — there's exactly one admin
account (see ADMIN_USERNAME/ADMIN_PASSWORD in app/config.py), so this is
about as simple as auth gets while still being safe:

  - Credentials are compared with hmac.compare_digest (constant-time, so
    a timing attack can't be used to guess the password character by
    character).
  - The "session" is a signed, timestamped token (via itsdangerous) baked
    straight into a cookie — there's no server-side session store to look
    up. The cookie IS the session; it can't be forged without knowing
    SECRET_KEY, and it self-expires after SESSION_MAX_AGE.
"""

import hmac

from fastapi import Cookie, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import get_settings

settings = get_settings()
SESSION_COOKIE = "admin_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours


def _serializer() -> URLSafeTimedSerializer:
    """itsdangerous serializer used to both create and verify session
    tokens. `salt` namespaces this specific use of SECRET_KEY, so a token
    made for one purpose can't accidentally be replayed for another if
    the same secret key is ever reused elsewhere."""
    return URLSafeTimedSerializer(settings.secret_key, salt="admin-session")


def check_credentials(username: str, password: str) -> bool:
    """Compares the submitted login form against the one configured admin
    account. Both comparisons run unconditionally (rather than short-
    circuiting on the first mismatch) via `and`, and hmac.compare_digest
    itself is constant-time — this avoids leaking, via response timing,
    which character of a guess was wrong."""
    valid_user = hmac.compare_digest(username, settings.admin_username)
    valid_pass = hmac.compare_digest(password, settings.admin_password)
    return valid_user and valid_pass


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
