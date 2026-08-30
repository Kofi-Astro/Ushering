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
    error = "Incorrect username or password." if request.query_params.get("error") else None
    return templates.TemplateResponse(request, "admin/login.html", {"error": error})


@router.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...)):
    if not check_credentials(username, password):
        return RedirectResponse(url="/login?error=1", status_code=303)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=60 * 60 * 12,
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
