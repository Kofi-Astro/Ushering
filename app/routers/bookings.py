"""The public Book Us form's submission endpoint. This is the ONLY route
in the whole project that's both public (no login) and writes to the
database — every other write goes through the password-protected admin
panel (app/admin/).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Booking
from ..schemas import BookingCreate

router = APIRouter(prefix="/api", tags=["bookings"])


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    """Called by the Book Us form's fetch() (app/static/js/main.js).
    FastAPI validates and parses the JSON body into `payload` automatically
    via the BookingCreate schema before this function even runs."""
    if payload.bot_field:
        # Honeypot tripped — pretend it worked so bots don't learn anything,
        # but don't actually store or act on it.
        return {"ok": True}

    booking = Booking(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        event_type=payload.event_type,
        event_date=payload.event_date,
        guest_count=payload.guest_count,
        location=payload.location,
        message=payload.message,
        # status defaults to BookingStatus.new (see app/models.py) —
        # nothing to set here; it shows up in the admin panel's "New"
        # filter immediately.
    )
    db.add(booking)
    db.commit()
    return {"ok": True}
