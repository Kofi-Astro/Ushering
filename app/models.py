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
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
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
    app/routers/bookings.py (customer-submitted fields only); everything
    else — reading the list, editing any field, updating status, deleting,
    and the payment-tracking fields below — happens in
    app/admin/routers/bookings.py, since only the business owner ever
    needs to touch those."""

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
    # An unguessable "password" a customer uses to reach their own
    # self-service manage-booking page (see app/routers/manage_booking.py)
    # without any real login — a plain 32-character hex UUID has 122 bits
    # of randomness, which is not practically guessable. Generated once at
    # booking creation and never changes; unique so it can double as a
    # lookup key. Never displayed to anyone except the customer (via their
    # confirmation email/the booking-success page) and the admin (for
    # support, in case a customer loses their link).
    manage_token: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: uuid.uuid4().hex)
    # Payment tracking, filled in by the business owner as an event moves
    # forward (never set by the public booking form) — free-text strings
    # rather than a strict decimal/currency type, consistent with how
    # guest_count is also just a string here: nothing in this app does
    # arithmetic on these, they're only ever displayed, so there's no
    # benefit to a rigid numeric type and it lets the owner write "GHS
    # 1,500" or "1500 cedis" or whatever's natural rather than fighting a
    # strict number field.
    amount_charged: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deposit_paid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # A plain string date (e.g. "2026-09-15"), same convention as
    # event_date above, filled in once the customer completes payment.
    full_payment_date: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Service(Base):
    """One of the 9 service types shown on the Home and Services pages
    (weddings, corporate events, funerals, ...). `order` controls display
    order everywhere (lower = earlier); the Home page additionally only
    shows the first 6 (see app/routers/pages.py:home)."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    # A Font Awesome icon class, e.g. "fa-solid fa-ring" — used
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
    """One tile in the Gallery page's grid, filterable by `category`
    (weddings/corporate/funerals/conferences/parties). Originally photos
    only; `media_type` now also allows "video".

    Videos are handled by URL only (YouTube, Vimeo, Facebook, Instagram,
    TikTok, or a direct .mp4/.webm link hosted elsewhere) rather than file
    upload — see app/admin/routers/gallery.py's docstring for why:
    Railway's disk is ephemeral and not sized for video, so self-hosting
    raw video files the same way photos are hosted would silently break
    on the next redeploy. `image`, for a video row, is repurposed as an
    optional poster/thumbnail (uploaded the same way a photo would be) —
    only skippable for a YouTube link, since app/content.py can derive a
    real thumbnail for those automatically; every other platform needs an
    uploaded poster to show anything but a generic icon in the grid.

    `is_hero` marks a video as eligible to play as the homepage hero's
    background/CTA media (see app/content.py:get_hero_videos) — more than
    one can be marked at once (they cycle/get their own "Watch" button,
    see templates/pages/index.html) — and is irrelevant for photos and
    for a video that isn't marked, which just displays in the regular
    grid like a photo does.
    """

    __tablename__ = "gallery_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    order: Mapped[int] = mapped_column(Integer, default=1)
    # Path under /images/uploads/ once a photo's been uploaded through the
    # admin panel (app/admin/routers/gallery.py); empty string shows a
    # placeholder icon tile instead (see templates/pages/gallery.html).
    # For a video row, doubles as an optional poster image (see class
    # docstring above).
    image: Mapped[str] = mapped_column(String(300), default="")
    # "image" or "video" — controls how app/content.py and the public
    # templates render this row. Kept as a plain string rather than an
    # Enum (contrast BookingStatus) since it's just a display switch, not
    # a business-process state machine.
    media_type: Mapped[str] = mapped_column(String(10), default="image")
    # A YouTube/Vimeo/Facebook/Instagram/TikTok link or a direct video
    # file URL, set only when media_type == "video". app/content.py
    # classifies which of those it is and builds the right playback
    # markup — never used directly by templates.
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_hero: Mapped[bool] = mapped_column(Boolean, default=False)


class FAQItem(Base):
    """One question/answer pair on the FAQ page."""

    __tablename__ = "faq_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(String(300))
    order: Mapped[int] = mapped_column(Integer, default=1)
    answer: Mapped[str] = mapped_column(Text)


class SiteText(Base):
    """One editable piece of free-form copy — a heading, paragraph, button
    label or similar wording baked into the page templates rather than
    already covered by Service/Testimonial/GalleryItem/FAQItem/
    SiteSetting. A generic key/value table rather than one column per
    string, since there are well over a hundred of these; the full
    catalog of keys (grouped by which page/section each belongs to, with
    its admin-facing label and starter value) lives in
    app/site_text_catalog.py, not here — this table just stores whatever
    the business owner has saved for each key. app/seed.py inserts every
    catalog key's default value once, so app/content.py:get_site_text
    never needs to handle a missing key, and the public templates never
    need a fallback in the `{{ site_text['some.key'] }}` lookup itself.
    """

    __tablename__ = "site_text"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)


class AdminAuth(Base):
    """Single-row table (id is always 1) holding whatever's needed for the
    admin password-reset flow — see app/security.py and
    app/admin/routers/auth.py. Doesn't exist at all until the first time
    either a reset is requested or a password is changed via one; until
    then, login falls back entirely to ADMIN_PASSWORD from the
    environment (see app/config.py) exactly as before this feature
    existed, so a fresh install works with zero extra setup.

    password_hash, once set, permanently takes over from the env var
    ADMIN_PASSWORD for that account (see security.check_credentials) —
    it's how a self-service reset actually changes the effective
    password, since there's no way for a running app to rewrite its own
    environment variables.
    """

    __tablename__ = "admin_auth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # A random, single-use token emailed as part of the reset link
    # (/reset-password/{token}), and its expiry — both cleared the moment
    # a reset actually completes, or naturally ignored once expired.
    reset_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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
