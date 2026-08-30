import hmac

from fastapi import Cookie, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import get_settings

settings = get_settings()
SESSION_COOKIE = "admin_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.secret_key, salt="admin-session")


def check_credentials(username: str, password: str) -> bool:
    valid_user = hmac.compare_digest(username, settings.admin_username)
    valid_pass = hmac.compare_digest(password, settings.admin_password)
    return valid_user and valid_pass


def create_session_token() -> str:
    return _serializer().dumps({"user": settings.admin_username})


def verify_session_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        _serializer().loads(token, max_age=SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_admin(admin_session: str | None = Cookie(default=None)) -> None:
    if not verify_session_token(admin_session):
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/login"},
        )
