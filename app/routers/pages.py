"""Every public-facing page on the site, plus /sitemap.xml and
/robots.txt. Each route follows the same shape: pull whatever content it
needs from app/content.py (which reads the database), pass it into
base_context() along with page-specific SEO metadata, and render the
matching template under app/templates/pages/.

None of this requires login — contrast with app/admin/routers/, which is
the entire separate, password-protected admin panel.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

from .. import content

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def base_context(request: Request, **extra) -> dict:
    """Template context every page needs regardless of what else it adds:
    the request itself (Jinja2Templates requires this), site-wide settings
    (contact info, social links — used by the shared topbar/navbar/footer
    partials), and the first 4 services for the footer's link list. Each
    route below calls this and layers its own title/description/keywords
    and page-specific data (services, gallery_items, etc.) on top via
    **extra.
    """
    return {
        "request": request,
        "settings": content.get_site_settings(),
        "footer_services": content.get_services()[:4],
        **extra,
    }


def _hero_video_context() -> dict:
    """Splits content.get_hero_videos() into the two ways
    templates/pages/index.html's hero section uses them (see that
    template's comment for why) and pre-serializes the direct-file ones
    into JSON for static/js/main.js's cycling logic — building that here
    rather than in the template keeps the "what does each video need for
    playback" logic in one place instead of duplicated in Jinja."""
    hero_videos = content.get_hero_videos()
    direct_videos = [v for v in hero_videos if v["direct_src"]]
    embed_videos = [v for v in hero_videos if v["embed_url"]]
    return {
        "hero_direct_videos": direct_videos,
        "hero_embed_videos": embed_videos,
        "hero_playlist_json": json.dumps(
            [{"src": v["direct_src"], "poster": v["image"] or None} for v in direct_videos]
        ),
    }


@router.get("/")
def home(request: Request):
    # Structured data (JSON-LD) describing the business for search engines
    # — rendered into a <script type="application/ld+json"> tag by
    # templates/base.html when `schema_json` is present in the context.
    # Built from the real site_settings row (not hardcoded) so it can
    # never silently drift back out of sync with what's shown on the page
    # itself — this block used to be a separate literal and kept the
    # original placeholder phone number and broken social links long
    # after the real ones were set everywhere else on the site.
    settings = content.get_site_settings()
    same_as = [
        url for url in (settings["facebook_url"], settings["instagram_url"], settings["tiktok_url"])
        if url and url != "#"
    ]
    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": settings["site_name"],
        "description": "Professional ushering and event support services for weddings, corporate events, funerals, conferences and special occasions across Ghana.",
        "areaServed": "Ghana",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Accra",
            "addressRegion": "Greater Accra",
            "addressCountry": "GH",
        },
        "telephone": f"+{settings['whatsapp_number']}",
        "email": settings["email"],
        "url": f"{settings['site_url']}/",
        "sameAs": same_as,
        "keywords": "ushering services, event ushers, professional ushers, wedding ushers, corporate event staff, event staffing, event support services, guest coordination, hospitality staff, event management support",
    }
    return templates.TemplateResponse(
        request,
        "pages/index.html",
        base_context(
            request,
            nav="home",
            # Lets the homepage's own gallery preview tiles open in the
            # same full-screen lightbox as the Gallery page (see
            # templates/base.html and static/js/main.js) — needed now that
            # those tiles can be real photos/videos, not just icons.
            lightbox=True,
            title="GPS Ushering and Events | Professional Ushers in Accra, Ghana",
            description="GPS Ushering and Events provides professional ushering and event support services across Ghana — weddings, corporate events, funerals, conferences, birthdays and concerts. Book trusted, elegant ushers today.",
            keywords="ushering services in Ghana, professional ushers in Accra, event ushers Ghana, corporate ushering services, wedding ushers in Accra, event staffing Ghana, hospitality staff Ghana, event support services Ghana, guest coordination services, ushering company Ghana, hire ushers Ghana, event management support",
            schema_json=json.dumps(schema),
            services=content.get_services()[:6],
            gallery_items=content.get_gallery_items()[:3],
            testimonials=content.get_testimonials()[:3],
            **_hero_video_context(),
        ),
    )


@router.get("/about.html")
def about(request: Request):
    # No page-specific content beyond base_context — this page is static
    # copy in templates/pages/about.html, just wrapped in the shared layout.
    return templates.TemplateResponse(
        request,
        "pages/about.html",
        base_context(
            request,
            nav="about",
            title="About Us | GPS Ushering and Events — Professional Ushers in Ghana",
            description="Learn about GPS Ushering and Events — a Ghana-based team of professional, trained ushers delivering elegant guest coordination and hospitality for weddings, corporate events and more.",
            keywords="ushering company Ghana, professional ushers in Accra, event ushers Ghana, trained ushers Ghana, event support team Accra, ushering services in Ghana, event staffing agency Ghana",
        ),
    )


@router.get("/services.html")
def services_page(request: Request):
    # Unlike the Home page's preview, this shows every service (all 9,
    # unsliced), each with its full description and highlights list.
    return templates.TemplateResponse(
        request,
        "pages/services.html",
        base_context(
            request,
            nav="services",
            title="Our Services | GPS Ushering and Events — Corporate Ushering Services",
            description="Explore GPS Ushering and Events' full range of services — wedding ushers in Accra, corporate ushering services, funeral support, conference registration, concert crowd control, church ushering and more.",
            keywords="corporate ushering services, wedding ushers in Accra, event ushers Ghana, professional ushers in Accra, funeral ushering Ghana, conference registration staff, event registration services, birthday party ushers Ghana, concert crowd control Ghana, church ushering services, brand activation staff Ghana, event staffing agency Ghana",
            services=content.get_services(),
        ),
    )


@router.get("/gallery.html")
def gallery_page(request: Request):
    # `lightbox=True` tells templates/base.html to include the click-to-
    # enlarge lightbox markup, which only this page's JS (app/static/js/
    # main.js) actually wires up — see main.js's "Gallery lightbox" block.
    return templates.TemplateResponse(
        request,
        "pages/gallery.html",
        base_context(
            request,
            nav="gallery",
            lightbox=True,
            title="Gallery | GPS Ushering and Events — Our Past Events in Ghana",
            description="Browse photos from weddings, corporate events, funerals, conferences and celebrations covered by GPS Ushering and Events across Ghana.",
            keywords="event ushers Ghana, professional ushers in Accra, wedding ushers in Accra, event staffing gallery Ghana, ushering portfolio Ghana, corporate event photos Ghana",
            gallery_items=content.get_gallery_items(),
        ),
    )


@router.get("/testimonials.html")
def testimonials_page(request: Request):
    # Shows every testimonial (Home page only shows the first 3 — see
    # the home() route above).
    return templates.TemplateResponse(
        request,
        "pages/testimonials.html",
        base_context(
            request,
            nav="testimonials",
            title="Testimonials | GPS Ushering and Events — Client Reviews",
            description="Read what event planners, couples, corporate clients and families across Ghana say about working with GPS Ushering and Events.",
            keywords="professional ushers in Accra, ushering services in Ghana, ushering company reviews Ghana, event staffing testimonials, client reviews event ushers",
            testimonials=content.get_testimonials(),
        ),
    )


@router.get("/faq.html")
def faq_page(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/faq.html",
        base_context(
            request,
            nav="faq",
            title="FAQ | GPS Ushering and Events — Frequently Asked Questions",
            description="Answers to common questions about booking GPS Ushering and Events for weddings, corporate events, funerals, conferences and more across Ghana.",
            keywords="professional ushers in Accra, ushering services in Ghana, event ushers Ghana, how to book ushers Ghana, hire event staff Ghana, ushering FAQ",
            faqs=content.get_faqs(),
        ),
    )


@router.get("/book-us.html")
def book_us_page(request: Request):
    # The booking form itself and the Leaflet map picker are entirely
    # client-side (see app/static/js/main.js and location-picker.js) —
    # this route just renders the page shell; the form POSTs to
    # /api/bookings (app/routers/bookings.py), not to this route.
    return templates.TemplateResponse(
        request,
        "pages/book-us.html",
        base_context(
            request,
            nav="book-us",
            title="Book Us | GPS Ushering and Events — Request a Quote",
            description="Book professional ushers for your wedding, corporate event, funeral, conference or celebration in Ghana. Get in touch by form, phone or WhatsApp.",
            keywords="wedding ushers in Accra, corporate ushering services, ushering services in Ghana, book ushers Ghana, hire ushers Accra, event staffing booking, wedding usher booking Ghana, corporate event staffing request",
        ),
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    """Tells search engine crawlers everything's allowed, and points them
    at the sitemap below. Generated dynamically (rather than a static
    file) so it always reflects the current site_url from Settings."""
    settings = content.get_site_settings()
    return f"User-agent: *\nAllow: /\n\nSitemap: {settings['site_url']}/sitemap.xml\n"


@router.get("/sitemap.xml")
def sitemap():
    """A hardcoded list of the site's own page URLs (there's no dynamic
    per-item pages like /services/123 to enumerate) turned into the
    minimal valid sitemap XML search engines expect."""
    settings = content.get_site_settings()
    urls = ["/", "/about.html", "/services.html", "/gallery.html", "/testimonials.html", "/faq.html", "/book-us.html"]
    body = "".join(f"<url><loc>{settings['site_url']}{u}</loc></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'
    return Response(content=xml, media_type="application/xml")
