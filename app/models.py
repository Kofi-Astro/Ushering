"""Every database table in the project. SQLAlchemy 2.x's typed
`Mapped[...]` style is used throughout — the type hint on the left (e.g.
`Mapped[str]` vs `Mapped[str | None]`) is what actually controls whether
a column is NOT NULL or nullable, not just documentation.

Two groups of tables:
  - Booking — written by the public Book Us form (app/routers/bookings.py),
    managed from the admin panel's Bookings section.
  - Service / Testimonial / GalleryItem / FAQItem / SiteSetting — the
    site's editable content. Only ever written to through the admin panel
    (app/admin/routers/*.py); read by the public pages via app/content.py.

app/seed.py populates all of these once, the first time the app runs
against an empty database.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class BookingStatus(str, enum.Enum):
    """The stages a booking inquiry moves through, tracked by the business
    owner in the admin panel's Bookings section. Inheriting from `str` as
    well as Enum means these compare equal to plain strings too (e.g.
    `booking.status == "new"` works), which is convenient in templates."""

    new = "new"
    contacted = "contacted"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


class Booking(Base):
    """One row per Book Us form submission. Created by
    app/routers/bookings.py; everything else (reading the list, updating
    status) happens in app/admin/routers/bookings.py."""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(100))
    # These three are optional on the form, so nullable here too.
    event_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    guest_count: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.new
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Service(Base):
    """One of the 9 service types shown on the Home and Services pages
    (weddings, corporate events, funerals, ...). `order` controls display
    order everywhere (lower = earlier); the Home page additionally only
    shows the first 6 (see app/routers/pages.py:home)."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    # A Font Awesome icon class, e.g. "fa-solid fa-rings-wedding" — used
    # directly as an HTML class attribute in the templates.
    icon: Mapped[str] = mapped_column(String(100), default="fa-solid fa-star")
    order: Mapped[int] = mapped_column(Integer, default=1)
    # Shorter blurb used in the Home page's service preview cards.
    home_description: Mapped[str] = mapped_column(Text)
    # Longer description used on the full Services page.
    description: Mapped[str] = mapped_column(Text)
    # Newline-separated in the admin form (one bullet per line); stored as
    # one text blob for simplicity and split back into a list when read —
    # see app/content.py:get_services.
    highlights: Mapped[str] = mapped_column(Text, default="")


class Testimonial(Base):
    """A client review. Shown on the Home page (first 3, newest-ordered)
    and in full on the Testimonials page."""

    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    role: Mapped[str] = mapped_column(String(150))
    rating: Mapped[int] = mapped_column(Integer, default=5)
    order: Mapped[int] = mapped_column(Integer, default=1)
    quote: Mapped[str] = mapped_column(Text)


class GalleryItem(Base):
    """One tile in the Gallery page's photo grid, filterable by
    `category` (weddings/corporate/funerals/conferences/parties)."""

    __tablename__ = "gallery_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    order: Mapped[int] = mapped_column(Integer, default=1)
    # Path under /images/uploads/ once a photo's been uploaded through the
    # admin panel (app/admin/routers/gallery.py); empty string shows a
    # placeholder icon tile instead (see templates/pages/gallery.html).
    image: Mapped[str] = mapped_column(String(300), default="")


class FAQItem(Base):
    """One question/answer pair on the FAQ page."""

    __tablename__ = "faq_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(String(300))
    order: Mapped[int] = mapped_column(Integer, default=1)
    answer: Mapped[str] = mapped_column(Text)


class SiteSetting(Base):
    """Single-row table (id is always 1) holding site-wide settings the
    business owner edits through the admin panel's Settings section —
    contact info, social links, branding text. Read everywhere on the
    public site via app/content.py:get_site_settings, which also supplies
    these same defaults if the row doesn't exist yet for some reason.
    """

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    site_name: Mapped[str] = mapped_column(String(200), default="GPS Ushering and Events")
    site_url: Mapped[str] = mapped_column(String(300), default="https://www.gpsusheringandevents.com")
    tagline: Mapped[str] = mapped_column(String(300), default="Ushering & Event Support Services")
    phone_display: Mapped[str] = mapped_column(String(50), default="+233 24 000 0000")
    # Digits only, with country code, no "+" or spaces — used to build
    # wa.me/<number> WhatsApp links and tel: links throughout the site.
    whatsapp_number: Mapped[str] = mapped_column(String(50), default="233240000000")
    email: Mapped[str] = mapped_column(String(200), default="info@gpsusheringandevents.com")
    address: Mapped[str] = mapped_column(String(300), default="Accra, Ghana")
    facebook_url: Mapped[str] = mapped_column(String(300), default="#")
    instagram_url: Mapped[str] = mapped_column(String(300), default="#")
    tiktok_url: Mapped[str] = mapped_column(String(300), default="#")
