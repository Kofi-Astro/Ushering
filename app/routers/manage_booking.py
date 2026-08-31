"""A customer's own self-service page for their booking, reached via the
unguessable link they get right after submitting the Book Us form (and
again in their confirmation email) — see app/models.py:Booking.manage_token
and app/routers/bookings.py, which generates it.

Deliberately NOT behind require_admin — the "password" here is simply
knowing the token, the same trust model as a password-reset link or a
calendar invite's edit link. Editing is only allowed while the booking is
still in EDITABLE_STATUSES: once the business has confirmed it, further
changes go through them directly rather than silently mutating a booking
they've already committed staff to.
"""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..content import get_site_settings
from ..database import get_db
from ..email_notify import send_customer_edit_notification
from ..models import Booking, BookingStatus
from .pages import base_context

router = APIRouter(tags=["manage-booking"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

EDITABLE_STATUSES = {BookingStatus.new, BookingStatus.contacted}


@router.get("/manage-booking/{token}")
def manage_booking_page(token: str, request: Request, saved: str | None = None, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.manage_token == token).first()
    return templates.TemplateResponse(
        request,
        "pages/manage_booking.html",
        base_context(
            request,
            title="Manage Your Booking | GPS Ushering and Events",
            description="View or update the details of your booking with GPS Ushering and Events.",
            nav=None,
            booking=booking,
            editable=bool(booking and booking.status in EDITABLE_STATUSES),
            saved=bool(saved),
        ),
    )


@router.post("/manage-booking/{token}")
def update_own_booking(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    event_type: str = Form(...),
    event_date: str = Form(""),
    guest_count: str = Form(""),
    location: str = Form(""),
    message: str = Form(""),
    db: Session = Depends(get_db),
):
    """Silently does nothing if the token doesn't match a booking, or if
    that booking is no longer editable (status moved past EDITABLE_STATUSES
    since the page was loaded) — always redirects back to the same page
    either way, which will show the current, real state either way."""
    booking = db.query(Booking).filter(Booking.manage_token == token).first()
    if booking and booking.status in EDITABLE_STATUSES:
        booking.name = name
        booking.phone = phone
        booking.email = email
        booking.event_type = event_type
        booking.event_date = event_date or None
        booking.guest_count = guest_count or None
        booking.location = location or None
        booking.message = message or None
        db.commit()

        manage_url = str(request.base_url).rstrip("/") + f"/manage-booking/{token}"
        background_tasks.add_task(
            send_customer_edit_notification,
            {
                "name": name,
                "phone": phone,
                "email": email,
                "event_type": event_type,
                "event_date": event_date or None,
                "guest_count": guest_count or None,
                "location": location or None,
                "message": message or None,
            },
            get_site_settings()["email"],
            manage_url,
        )

    return RedirectResponse(url=f"/manage-booking/{token}?saved=1", status_code=303)
