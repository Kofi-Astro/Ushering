"""Login and logout for the admin panel. No Depends(require_admin) here,
obviously — these are the routes that exist precisely so someone who
ISN'T yet authenticated can become authenticated.
"""

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ...config import get_settings
from ...security import SESSION_COOKIE, check_credentials, create_session_token

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))
settings = get_settings()


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    """Renders the login page. A `?error=1` query param (added by the
    redirect in login_submit below) shows an error message."""
    error = "Incorrect username or password." if request.query_params.get("error") else None
    return templates.TemplateResponse(request, "admin/login.html", {"error": error})


@router.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...)):
    """Handles the login form's submit. On success, issues the signed
    session cookie (see app/security.py) and redirects to the dashboard;
    on failure, redirects back to the login form with an error flag."""
    if not check_credentials(username, password):
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
