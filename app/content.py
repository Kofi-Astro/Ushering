"""Read-side helpers for the site's editable content — services, gallery,
testimonials, FAQ and site-wide settings. All of it lives in the database
now (see app/models.py) and is edited through the admin panel at
/services, /gallery, /testimonials, /faq and /settings. This module is
just the shape-conversion layer between the DB rows and what the public
page templates expect (kept stable so app/routers/pages.py and the
templates under app/templates/pages/ didn't need to change).

Every function here opens its own short-lived session (`with
SessionLocal() as db:`) and returns plain dicts/lists rather than
SQLAlchemy objects — these run outside of any FastAPI request dependency,
so there's no `Depends(get_db)` session to reuse, and plain dicts are
simplest for Jinja2 templates to consume (`{{ service.title }}` works on
a dict the same way it would on an object's attribute).

Nothing here is cached: every call re-queries the database, so an edit
made through the admin panel is visible on the very next public page
request with no cache to invalidate.
"""

import re
from urllib.parse import parse_qs, urlparse

import markdown as md

from .database import SessionLocal
from .models import FAQItem, GalleryItem, Service, SiteSetting, Testimonial


def get_services() -> list[dict]:
    """All services, ordered for display. Used in full on the Services
    page; the Home page route slices this down to the first 6 itself
    (see app/routers/pages.py:home)."""
    with SessionLocal() as db:
        rows = db.query(Service).order_by(Service.order).all()
        return [
            {
                "id": s.id,
                "title": s.title,
                "icon": s.icon,
                "order": s.order,
                # Renamed from the DB column home_description to match
                # what templates/pages/index.html expects.
                "homeDescription": s.home_description,
                "description": s.description,
                # DB stores highlights as one newline-separated blob (see
                # app/models.py:Service.highlights); split it back into a
                # list of non-empty lines for the template's {% for %} loop.
                "highlights": [line.strip() for line in s.highlights.splitlines() if line.strip()],
            }
            for s in rows
        ]


def get_testimonials() -> list[dict]:
    """All testimonials, ordered for display. Home page shows the first 3;
    the Testimonials page shows all of them."""
    with SessionLocal() as db:
        rows = db.query(Testimonial).order_by(Testimonial.order).all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "role": t.role,
                "rating": t.rating,
                "order": t.order,
                # The quote is stored as plain text; running it through
                # markdown lets an admin optionally use *emphasis* etc.,
                # and wraps it in a <p> for free either way.
                "body_html": md.markdown(t.quote.strip()) if t.quote else "",
            }
            for t in rows
        ]


def get_gallery_items() -> list[dict]:
    """All gallery photos, ordered for display. `image` is either a path
    under /images/uploads/ (once a real photo's been uploaded through the
    admin panel) or an empty string, which the gallery template treats as
    "show the placeholder icon tile instead"."""
    with SessionLocal() as db:
        rows = db.query(GalleryItem).order_by(GalleryItem.order).all()
        return [
            {
                "id": g.id,
                "label": g.label,
                "category": g.category,
                "order": g.order,
                "image": g.image,
            }
            for g in rows
        ]


def get_faqs() -> list[dict]:
    """All FAQ entries, ordered for display."""
    with SessionLocal() as db:
        rows = db.query(FAQItem).order_by(FAQItem.order).all()
        return [
            {
                "id": f.id,
                "question": f.question,
                "order": f.order,
                "body_html": md.markdown(f.answer.strip()) if f.answer else "",
            }
            for f in rows
        ]


def _handle_from_url(url: str | None, at: bool = True) -> str | None:
    """Derives a displayable handle from a social profile URL's last path
    segment — e.g. https://www.instagram.com/foo -> "@foo". Returns None
    for an unset/placeholder URL ("#" or empty) so templates can skip the
    line entirely rather than render a broken-looking handle. Facebook
    page names are conventionally shown without the "@" (at=False).

    A facebook.com/search/... URL (used as a stand-in until a page's real
    URL is confirmed — see app/routers/pages.py:home's use of it) has no
    real page-name path segment to read, just a generic word like "top" -
    for that shape specifically, fall back to the search query string
    itself so the footer shows the actual business name being searched
    for rather than a meaningless word.

    A personal Facebook profile used to promote the business (rather than
    a dedicated Page) has a slug like "firstname.lastname.1234" — the
    trailing digits are Facebook's disambiguation suffix for common names,
    not part of the name. Stripped and title-cased into "Firstname
    Lastname" for a readable label instead of a raw slug.
    """
    if not url or url == "#":
        return None
    parsed = urlparse(url)
    segment = parsed.path.strip("/").split("/")[-1]
    if not segment or segment in {"search", "top", "pages", "people"}:
        query = parse_qs(parsed.query).get("q", [None])[0]
        return query or None
    if not at:
        name_only = re.sub(r"\.\d+$", "", segment)
        if name_only != segment:
            return name_only.replace(".", " ").replace("-", " ").title()
    if at and not segment.startswith("@"):
        return f"@{segment}"
    return segment


def get_site_settings() -> dict:
    """Site-wide contact info, social links and branding text — injected
    into every page's context (see app/routers/pages.py:base_context) and
    referenced throughout the templates as `settings.phone_display`,
    `settings.whatsapp_number`, etc.

    Falls back to a fresh (unsaved) SiteSetting()'s defaults if the single
    settings row doesn't exist yet, so the site never breaks even before
    app/seed.py or a first admin save has created it.
    """
    with SessionLocal() as db:
        row = db.query(SiteSetting).filter(SiteSetting.id == 1).first()
        if row is None:
            row = SiteSetting(id=1)
        return {
            "site_name": row.site_name,
            "site_url": row.site_url,
            "tagline": row.tagline,
            "phone_display": row.phone_display,
            "whatsapp_number": row.whatsapp_number,
            "email": row.email,
            "address": row.address,
            "facebook_url": row.facebook_url,
            "instagram_url": row.instagram_url,
            "tiktok_url": row.tiktok_url,
            "facebook_handle": _handle_from_url(row.facebook_url, at=False),
            "instagram_handle": _handle_from_url(row.instagram_url),
            "tiktok_handle": _handle_from_url(row.tiktok_url),
        }
