"""The admin panel's Bookings section — lists every Book Us submission,
filterable by status, with a per-row form to move a booking through the
new -> contacted -> confirmed -> completed (or cancelled) workflow, a full
edit page for changing any of the customer's original details (a customer
might call to move their event date, add guests, etc.) and recording
payment progress (amount charged, deposit paid, when full payment came
in), and a delete button for clearing out entries the business owner no
longer needs to keep around (spam/test submissions, old cancelled
bookings, etc.).

There's no create here — bookings are only ever created by the public
form (app/routers/bookings.py).
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...content import get_site_settings
from ...database import get_db
from ...models import Booking, BookingStatus
from ...security import require_admin

router = APIRouter(prefix="/bookings", tags=["bookings-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("")
def list_bookings(request: Request, status: str | None = None, db: Session = Depends(get_db)):
    """Lists bookings newest-first, optionally filtered to one status via
    ?status=new etc. (the filter tabs in admin/bookings.html link here).
    Also computes a count per status for those tabs' "(N)" badges."""
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
        "admin/bookings.html",
        {
            "title": "Bookings",
            "active": "bookings",
            "bookings": bookings,
            "active_status": status,
            "counts": counts,
        },
    )


@router.post("/{booking_id}/status")
def update_status(booking_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    """Handles the per-booking status dropdown + Update button in
    admin/bookings.html. Silently does nothing if the id doesn't exist
    (shouldn't happen in normal use, but no need to error over it) and
    then always redirects back to the list either way."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.status = BookingStatus(status)
        db.commit()
    return RedirectResponse(url="/bookings", status_code=303)


@router.get("/{booking_id}/edit")
def edit_booking_form(booking_id: int, request: Request, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    # Built from settings.site_url, not this request's own host — this
    # route is served on the admin subdomain, which is a different host
    # entirely from where /manage-booking/{token} actually lives.
    manage_url = None
    if booking:
        site_url = get_site_settings()["site_url"].rstrip("/")
        manage_url = f"{site_url}/manage-booking/{booking.manage_token}"
    return templates.TemplateResponse(
        request,
        "admin/booking_form.html",
        {
            "title": "Edit Booking",
            "active": "bookings",
            "booking": booking,
            "statuses": list(BookingStatus),
            "manage_url": manage_url,
        },
    )


@router.post("/{booking_id}/edit")
def update_booking(
    booking_id: int,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    event_type: str = Form(...),
    event_date: str = Form(""),
    guest_count: str = Form(""),
    location: str = Form(""),
    message: str = Form(""),
    status: str = Form(...),
    amount_charged: str = Form(""),
    deposit_paid: str = Form(""),
    full_payment_date: str = Form(""),
    db: Session = Depends(get_db),
):
    """Handles the full edit form (admin/booking_form.html) — every field
    the customer originally submitted, plus status and the payment-
    tracking fields, all in one save. Optional text fields come in as
    empty strings from unfilled form inputs rather than None, so they're
    normalized to None below to match how the public booking form stores
    "not provided" (see app/routers/bookings.py) — keeps the two write
    paths consistent rather than one using "" and the other using null
    for the same "nothing here" meaning."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.name = name
        booking.phone = phone
        booking.email = email
        booking.event_type = event_type
        booking.event_date = event_date or None
        booking.guest_count = guest_count or None
        booking.location = location or None
        booking.message = message or None
        booking.status = BookingStatus(status)
        booking.amount_charged = amount_charged or None
        booking.deposit_paid = deposit_paid or None
        booking.full_payment_date = full_payment_date or None
        db.commit()
    return RedirectResponse(url="/bookings", status_code=303)


@router.post("/{booking_id}/delete")
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    """Handles the Delete button on each booking card (which confirms via
    a JS `confirm()` dialog before submitting — see admin/bookings.html).
    Permanent, with no undo — appropriate for clearing out old cancelled
    bookings, spam, or test submissions."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        db.delete(booking)
        db.commit()
    return RedirectResponse(url="/bookings", status_code=303)
