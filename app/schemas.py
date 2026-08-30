"""Pydantic schemas for the booking API — these are the request/response
shapes, distinct from the SQLAlchemy models in app/models.py (which are
the database row shapes). FastAPI uses BookingCreate to validate/parse the
incoming JSON body of POST /api/bookings.

BookingOut isn't currently used by any route (there's no public "list
bookings" endpoint — that's admin-only and rendered as HTML, not JSON) but
is kept as the natural shape for a future read API if one's ever needed.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .models import BookingStatus


class BookingCreate(BaseModel):
    """What the Book Us form's fetch() call sends as JSON. Field names
    match the HTML form's `name` attributes exactly (see
    templates/pages/book-us.html), since the frontend JS just serializes
    the form fields as-is — see app/static/js/main.js's booking-form
    submit handler."""

    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=1, max_length=50)
    email: EmailStr
    event_type: str = Field(min_length=1, max_length=100)
    event_date: str | None = None
    guest_count: str | None = None
    location: str | None = None
    message: str | None = None
    # Honeypot field: real users never fill this in (it's visually hidden
    # on the form). If it has a value, the submission is silently dropped
    # as spam — see app/routers/bookings.py.
    bot_field: str | None = None


class BookingOut(BaseModel):
    """The shape a Booking row would take if ever returned as JSON."""

    id: int
    name: str
    phone: str
    email: str
    event_type: str
    event_date: str | None
    guest_count: str | None
    location: str | None
    message: str | None
    status: BookingStatus
    created_at: datetime

    # Lets Pydantic build this straight from a SQLAlchemy Booking object
    # (reading its attributes) instead of requiring a plain dict.
    model_config = {"from_attributes": True}
