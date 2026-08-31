"""The public Book Us form's submission endpoint. This is the ONLY route
in the whole project that's both public (no login) and writes to the
database — every other write goes through the password-protected admin
panel (app/admin/).
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from ..content import get_site_settings
from ..database import get_db
from ..email_notify import send_booking_notification
from ..models import Booking
from ..schemas import BookingCreate

router = APIRouter(prefix="/api", tags=["bookings"])


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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

    # Runs after this function returns the response below, so the customer
    # isn't kept waiting on an SMTP round trip just to see "booking sent".
    # Built from `payload` (not the `booking` ORM object, which would be
    # unsafe to touch once its session closes — see app/email_notify.py).
    # The recipient is the business's own admin-editable email address
    # (site_settings.email), not a separate hardcoded address to keep in
    # sync.
    background_tasks.add_task(
        send_booking_notification,
        {
            "name": payload.name,
            "phone": payload.phone,
            "email": payload.email,
            "event_type": payload.event_type,
            "event_date": payload.event_date,
            "guest_count": payload.guest_count,
            "location": payload.location,
            "message": payload.message,
        },
        get_site_settings()["email"],
    )

    return {"ok": True}
