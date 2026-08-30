from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Booking
from ..schemas import BookingCreate

router = APIRouter(prefix="/api", tags=["bookings"])


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
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
    )
    db.add(booking)
    db.commit()
    return {"ok": True}
