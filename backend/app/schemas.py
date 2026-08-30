from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .models import BookingStatus


class BookingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=1, max_length=50)
    email: EmailStr
    event_type: str = Field(min_length=1, max_length=100)
    event_date: str | None = None
    guest_count: str | None = None
    location: str | None = None
    message: str | None = None
    # Honeypot field: real users never fill this in. If it has a value,
    # the submission is silently dropped as spam.
    bot_field: str | None = None


class BookingOut(BaseModel):
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

    model_config = {"from_attributes": True}
