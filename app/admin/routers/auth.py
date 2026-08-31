"""Login, logout, and password reset for the admin panel. No
Depends(require_admin) anywhere in this file, obviously — these are the
routes that exist precisely so someone who ISN'T yet authenticated can
become authenticated (or recover the ability to).
"""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...config import get_settings
from ...content import get_site_settings
from ...database import get_db
from ...email_notify import send_password_reset_email
from ...security import (
    SESSION_COOKIE,
    check_credentials,
    create_reset_token,
    create_session_token,
    hash_password,
    verify_reset_token,
)

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))
settings = get_settings()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    """Renders the login page. `?error=1` (added by login_submit below)
    shows an error message; `?reset=1` (added by reset_password_submit)
    shows a "password changed" success message instead."""
    error = "Incorrect username or password." if request.query_params.get("error") else None
    reset = bool(request.query_params.get("reset"))
    return templates.TemplateResponse(request, "admin/login.html", {"error": error, "reset": reset})


@router.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Handles the login form's submit. On success, issues the signed
    session cookie (see app/security.py) and redirects to the dashboard;
    on failure, redirects back to the login form with an error flag."""
    if not check_credentials(username, password, db):
        return RedirectResponse(url="/login?error=1", status_code=303)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(),
        httponly=True,  # not readable from JS — mitigates XSS cookie theft
        samesite="lax",
        # Real browsers silently drop a Secure cookie over plain http://,
        # which is why COOKIE_SECURE must be false for local dev but
        # should always be true once deployed behind HTTPS.
        secure=settings.cookie_secure,
        max_age=60 * 60 * 12,  # matches security.SESSION_MAX_AGE
    )
    return response


@router.post("/logout")
def logout():
    """Clears the session cookie and sends the admin back to the login
    page. A POST (not a GET) so logging out can't be triggered by, say, an
    <img> tag or link prefetch pointing at this URL."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_form(request: Request, sent: str | None = None):
    """There's exactly one admin account, so this asks for nothing beyond
    a confirmation click — the email it sends to is always the business's
    own site_settings.email, never something typed in here (which would
    just be an unauthenticated way to redirect the reset link anywhere)."""
    return templates.TemplateResponse(request, "admin/forgot_password.html", {"sent": bool(sent)})


@router.post("/forgot-password")
def forgot_password_submit(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Always redirects to the same "check your email" state regardless of
    whether SMTP is actually configured — see
    email_notify.send_password_reset_email for why this specific email
    can't have an on-screen fallback the way the booking manage_url does."""
    token = create_reset_token(db)
    reset_url = str(request.base_url).rstrip("/") + f"/reset-password/{token}"
    background_tasks.add_task(send_password_reset_email, reset_url, get_site_settings()["email"])
    return RedirectResponse(url="/forgot-password?sent=1", status_code=303)


@router.get("/reset-password/{token}", response_class=HTMLResponse)
def reset_password_form(token: str, request: Request, db: Session = Depends(get_db)):
    valid = verify_reset_token(token, db) is not None
    return templates.TemplateResponse(request, "admin/reset_password.html", {"token": token, "valid": valid})


@router.post("/reset-password/{token}")
def reset_password_submit(
    token: str, request: Request, password: str = Form(...), confirm_password: str = Form(...), db: Session = Depends(get_db)
):
    admin_auth = verify_reset_token(token, db)
    if not admin_auth or password != confirm_password or len(password) < 8:
        # Same page, still showing the form — reset_password.html reads
        # `error` to explain which of the above went wrong without
        # needing a second round trip through /reset-password/{token}.
        valid = admin_auth is not None
        error = (
            "This reset link is invalid or has expired."
            if not valid
            else "Passwords must match and be at least 8 characters."
        )
        return templates.TemplateResponse(
            request, "admin/reset_password.html", {"token": token, "valid": valid, "error": error}
        )

    admin_auth.password_hash = hash_password(password)
    admin_auth.reset_token = None
    admin_auth.reset_token_expires = None
    db.commit()
    return RedirectResponse(url="/login?reset=1", status_code=303)
