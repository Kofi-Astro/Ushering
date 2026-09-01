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
from urllib.parse import parse_qs, quote, urlparse

import markdown as md

from .database import SessionLocal
from .models import FAQItem, GalleryItem, Service, SiteSetting, SiteText, Testimonial
from .site_text_catalog import all_fields


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


_YOUTUBE_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([\w-]{11})")
_VIMEO_RE = re.compile(r"vimeo\.com/(?:video/)?(\d+)")
_FACEBOOK_VIDEO_RE = re.compile(r"(?:facebook\.com|fb\.watch)/")
_INSTAGRAM_RE = re.compile(r"instagram\.com/(p|reel|tv)/([\w-]+)")
_TIKTOK_RE = re.compile(r"tiktok\.com/@[\w.-]+/video/(\d+)")
_VIDEO_FILE_EXTENSIONS = (".mp4", ".webm", ".ogg", ".mov")


def _analyze_video_url(video_url: str | None) -> dict:
    """Classifies a GalleryItem's video_url into exactly one playback
    strategy, so templates never parse URLs themselves:
      - a direct file link (.mp4/.webm/.ogg/.mov) plays in a plain
        <video> tag (`direct_src`)
      - a YouTube, Vimeo, Facebook, Instagram or TikTok link plays in an
        <iframe> embed (`embed_url`) — YouTube additionally gets a real
        thumbnail (`thumb_url`) derived from the video ID; the others
        don't expose one without an API call this read-only, no-network
        function deliberately avoids, so those fall back to an uploaded
        poster image (see app/models.py:GalleryItem) or a generic icon
      - anything unrecognized (or blank) plays nothing, same as if
        video_url were never set

    Autoplay is baked directly into `embed_url` (rather than appended by
    the caller) wherever a platform actually supports it via a query
    param, since Facebook's URL already has one of its own (`href=...`)
    and blindly appending `?autoplay=1` on top of that would produce a
    broken double-`?` URL. Instagram's and TikTok's embeds don't offer a
    reliable autoplay param at all, so those just open paused — clicking
    the tile still opens the lightbox, the visitor presses play once
    inside it.
    """
    url = (video_url or "").strip()
    if not url:
        return {"direct_src": None, "embed_url": None, "thumb_url": None}
    if url.lower().split("?")[0].endswith(_VIDEO_FILE_EXTENSIONS):
        return {"direct_src": url, "embed_url": None, "thumb_url": None}
    youtube_match = _YOUTUBE_RE.search(url)
    if youtube_match:
        video_id = youtube_match.group(1)
        return {
            "direct_src": None,
            "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}?autoplay=1",
            "thumb_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        }
    vimeo_match = _VIMEO_RE.search(url)
    if vimeo_match:
        return {
            "direct_src": None,
            "embed_url": f"https://player.vimeo.com/video/{vimeo_match.group(1)}?autoplay=1",
            "thumb_url": None,
        }
    instagram_match = _INSTAGRAM_RE.search(url)
    if instagram_match:
        kind, shortcode = instagram_match.groups()
        return {
            "direct_src": None,
            "embed_url": f"https://www.instagram.com/{kind}/{shortcode}/embed",
            "thumb_url": None,
        }
    tiktok_match = _TIKTOK_RE.search(url)
    if tiktok_match:
        return {
            "direct_src": None,
            "embed_url": f"https://www.tiktok.com/embed/v2/{tiktok_match.group(1)}",
            "thumb_url": None,
        }
    # Checked last, and just for the domain rather than a specific path
    # shape: a shared Facebook video link's URL itself becomes the
    # `href` the Video Plugin loads, so (unlike the platforms above)
    # there's no ID to extract — any facebook.com/fb.watch link is
    # assumed to be a video link, since that's the only thing this field
    # is ever used for. A vm.tiktok.com/fb.watch *short* link (rather
    # than the full copied-from-browser one) can't be classified this
    # way either, since resolving it needs a network request — out of
    # scope for this function, and rare in practice since "Copy Link"
    # from a desktop browser already gives the full form.
    if _FACEBOOK_VIDEO_RE.search(url):
        return {
            "direct_src": None,
            "embed_url": f"https://www.facebook.com/plugins/video.php?href={quote(url, safe='')}&show_text=false&autoplay=true",
            "thumb_url": None,
        }
    return {"direct_src": None, "embed_url": None, "thumb_url": None}


def _gallery_item_dict(g: GalleryItem) -> dict:
    video = _analyze_video_url(g.video_url) if g.media_type == "video" else _analyze_video_url(None)
    return {
        "id": g.id,
        "label": g.label,
        "category": g.category,
        "order": g.order,
        "image": g.image,
        "media_type": g.media_type,
        "is_hero": g.is_hero,
        **video,
    }


def get_gallery_items() -> list[dict]:
    """All gallery tiles (photos and videos), ordered for display. `image`
    is either a path under /images/uploads/ (once uploaded through the
    admin panel) or an empty string; for a video row it's an optional
    poster image rather than the primary media — see
    app/models.py:GalleryItem's docstring."""
    with SessionLocal() as db:
        rows = db.query(GalleryItem).order_by(GalleryItem.order).all()
        return [_gallery_item_dict(g) for g in rows]


def get_hero_videos() -> list[dict]:
    """Every video marked "Feature as hero video" in the admin Gallery
    section, ordered for display (see app/routers/pages.py:home and
    templates/pages/index.html). Split into two different treatments
    there, by which of `direct_src`/`embed_url` each ends up with: direct
    file videos cycle silently through the homepage hero's background,
    advancing to the next one as each finishes (see the hero-playlist
    block in static/js/main.js); YouTube/Vimeo videos can't autoplay
    silently in the background the same way, so each instead gets its own
    "Watch" button that opens it in the lightbox on click."""
    with SessionLocal() as db:
        rows = (
            db.query(GalleryItem)
            .filter(GalleryItem.media_type == "video", GalleryItem.is_hero.is_(True))
            .order_by(GalleryItem.order)
            .all()
        )
        return [_gallery_item_dict(g) for g in rows]


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


def get_site_text() -> dict[str, str]:
    """Every editable copy block (headings, paragraphs, button labels —
    see app/site_text_catalog.py for the full catalog of keys and what
    each one is), keyed by its dotted name. Injected into every page's
    context (see app/routers/pages.py:base_context) as `site_text`, so
    templates do `{{ site_text['home.hero.title'] }}` instead of hardcoding
    the copy directly — one query loads every key at once rather than a
    separate round trip per string.

    Falls back to the catalog's own default for any key missing from the
    database (there shouldn't be one — app/seed.py inserts every catalog
    key's default the first time the app runs — but a key added to the
    catalog after that first run, without a matching migration/backfill,
    would otherwise render as blank instead of its intended starter text)."""
    with SessionLocal() as db:
        saved = {row.key: row.value for row in db.query(SiteText).all()}
    return {f.key: saved.get(f.key, f.default) for f in all_fields()}
