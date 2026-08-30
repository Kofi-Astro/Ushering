"""The admin panel's Bookings section — lists every Book Us submission,
filterable by status, with a per-row form to move a booking through the
new -> contacted -> confirmed -> completed (or cancelled) workflow.

This is read/update only — there's no create or delete here, since
bookings are only ever created by the public form (app/routers/bookings.py)
and there's no legitimate reason for one to be deleted rather than marked
cancelled.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

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
