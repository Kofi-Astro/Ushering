import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class BookingStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(100))
    event_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    guest_count: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.new
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str] = mapped_column(String(100), default="fa-solid fa-star")
    order: Mapped[int] = mapped_column(Integer, default=1)
    home_description: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    # Newline-separated in the admin form; stored as one text blob for
    # simplicity and split back into a list when read (see app/content.py).
    highlights: Mapped[str] = mapped_column(Text, default="")


class Testimonial(Base):
    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(150))
    rating: Mapped[int] = mapped_column(Integer, default=5)
    order: Mapped[int] = mapped_column(Integer, default=1)
    quote: Mapped[str] = mapped_column(Text)


class GalleryItem(Base):
    __tablename__ = "gallery_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    order: Mapped[int] = mapped_column(Integer, default=1)
    # Path under /images/uploads/, or empty for the placeholder icon tile.
    image: Mapped[str] = mapped_column(String(300), default="")


class FAQItem(Base):
    __tablename__ = "faq_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(String(300))
    order: Mapped[int] = mapped_column(Integer, default=1)
    answer: Mapped[str] = mapped_column(Text)


class SiteSetting(Base):
    """Single-row table (id is always 1) holding site-wide settings the
    business owner edits through /settings — contact info, social links,
    branding text. See app/content.py:get_site_settings for the defaults
    used if this row doesn't exist yet.
    """

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    site_name: Mapped[str] = mapped_column(String(200), default="GPS Ushering and Events")
    site_url: Mapped[str] = mapped_column(String(300), default="https://www.gpsusheringandevents.com")
    tagline: Mapped[str] = mapped_column(String(300), default="Ushering & Event Support Services")
    phone_display: Mapped[str] = mapped_column(String(50), default="+233 24 000 0000")
    whatsapp_number: Mapped[str] = mapped_column(String(50), default="233240000000")
    email: Mapped[str] = mapped_column(String(200), default="info@gpsusheringandevents.com")
    address: Mapped[str] = mapped_column(String(300), default="Accra, Ghana")
    facebook_url: Mapped[str] = mapped_column(String(300), default="#")
    instagram_url: Mapped[str] = mapped_column(String(300), default="#")
    tiktok_url: Mapped[str] = mapped_column(String(300), default="#")
