from pathlib import Path

from fastapi import APIRouter, Cookie, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Booking, BookingStatus
from ..security import (
    SESSION_COOKIE,
    check_credentials,
    create_session_token,
    verify_session_token,
)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
settings = get_settings()


def _require_admin(admin_session: str | None = Cookie(default=None)) -> bool:
    return verify_session_token(admin_session)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    error = "Incorrect username or password." if request.query_params.get("error") else None
    return templates.TemplateResponse(request, "login.html", {"error": error})


@router.post("/login")
def login_submit(username: str = Form(...), password: str = Form(...)):
    if not check_credentials(username, password):
        return RedirectResponse(url="/admin/login?error=1", status_code=303)
    response = RedirectResponse(url="/admin", status_code=303)
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
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    status: str | None = None,
    db: Session = Depends(get_db),
    is_admin: bool = Depends(_require_admin),
):
    if not is_admin:
        return RedirectResponse(url="/admin/login", status_code=303)

    query = db.query(Booking).order_by(Booking.created_at.desc())
    if status:
        query = query.filter(Booking.status == status)
    bookings = query.all()

    counts_query = db.query(Booking.status, func.count(Booking.id)).group_by(Booking.status).all()
    counts = {s.value: 0 for s in BookingStatus}
    counts["all"] = db.query(func.count(Booking.id)).scalar() or 0
    for status_value, count in counts_query:
        counts[status_value.value] = count

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"bookings": bookings, "active_status": status, "counts": counts},
    )


@router.post("/bookings/{booking_id}/status")
def update_status(
    booking_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    is_admin: bool = Depends(_require_admin),
):
    if not is_admin:
        return RedirectResponse(url="/admin/login", status_code=303)

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.status = BookingStatus(status)
        db.commit()
    return RedirectResponse(url="/admin", status_code=303)
