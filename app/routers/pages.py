import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

from .. import content

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def base_context(request: Request, **extra) -> dict:
    return {
        "request": request,
        "settings": content.get_site_settings(),
        "footer_services": content.get_services()[:4],
        **extra,
    }


@router.get("/")
def home(request: Request):
    schema = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": "GPS Ushering and Events",
        "description": "Professional ushering and event support services for weddings, corporate events, funerals, conferences and special occasions across Ghana.",
        "areaServed": "Ghana",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Accra",
            "addressRegion": "Greater Accra",
            "addressCountry": "GH",
        },
        "telephone": "+233240000000",
        "url": "https://www.gpsusheringandevents.com/",
        "sameAs": ["https://facebook.com/", "https://instagram.com/"],
    }
    return templates.TemplateResponse(
        request,
        "pages/index.html",
        base_context(
            request,
            nav="home",
            title="GPS Ushering and Events | Professional Ushers in Accra, Ghana",
            description="GPS Ushering and Events provides professional ushering and event support services across Ghana — weddings, corporate events, funerals, conferences, birthdays and concerts. Book trusted, elegant ushers today.",
            keywords="ushering services in Ghana, professional ushers in Accra, event ushers Ghana, corporate ushering services, wedding ushers in Accra",
            schema_json=json.dumps(schema),
            services=content.get_services()[:6],
            gallery_items=content.get_gallery_items()[:3],
            testimonials=content.get_testimonials()[:3],
        ),
    )


@router.get("/about.html")
def about(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/about.html",
        base_context(
            request,
            nav="about",
            title="About Us | GPS Ushering and Events — Professional Ushers in Ghana",
            description="Learn about GPS Ushering and Events — a Ghana-based team of professional, trained ushers delivering elegant guest coordination and hospitality for weddings, corporate events and more.",
            keywords="ushering services in Ghana, professional ushers in Accra, event ushers Ghana",
        ),
    )


@router.get("/services.html")
def services_page(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/services.html",
        base_context(
            request,
            nav="services",
            title="Our Services | GPS Ushering and Events — Corporate Ushering Services",
            description="Explore GPS Ushering and Events' full range of services — wedding ushers in Accra, corporate ushering services, funeral support, conference registration and more.",
            keywords="corporate ushering services, wedding ushers in Accra, event ushers Ghana, professional ushers in Accra",
            services=content.get_services(),
        ),
    )


@router.get("/gallery.html")
def gallery_page(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/gallery.html",
        base_context(
            request,
            nav="gallery",
            lightbox=True,
            title="Gallery | GPS Ushering and Events — Our Past Events in Ghana",
            description="Browse photos from weddings, corporate events, funerals, conferences and celebrations covered by GPS Ushering and Events across Ghana.",
            keywords="event ushers Ghana, professional ushers in Accra, wedding ushers in Accra",
            gallery_items=content.get_gallery_items(),
        ),
    )


@router.get("/testimonials.html")
def testimonials_page(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/testimonials.html",
        base_context(
            request,
            nav="testimonials",
            title="Testimonials | GPS Ushering and Events — Client Reviews",
            description="Read what event planners, couples, corporate clients and families across Ghana say about working with GPS Ushering and Events.",
            keywords="professional ushers in Accra, ushering services in Ghana",
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
            keywords="professional ushers in Accra, ushering services in Ghana, event ushers Ghana",
            faqs=content.get_faqs(),
        ),
    )


@router.get("/book-us.html")
def book_us_page(request: Request):
    return templates.TemplateResponse(
        request,
        "pages/book-us.html",
        base_context(
            request,
            nav="book-us",
            title="Book Us | GPS Ushering and Events — Request a Quote",
            description="Book professional ushers for your wedding, corporate event, funeral, conference or celebration in Ghana. Get in touch by form, phone or WhatsApp.",
            keywords="wedding ushers in Accra, corporate ushering services, ushering services in Ghana",
        ),
    )


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    settings = content.get_site_settings()
    return f"User-agent: *\nAllow: /\n\nSitemap: {settings['site_url']}/sitemap.xml\n"


@router.get("/sitemap.xml")
def sitemap():
    settings = content.get_site_settings()
    urls = ["/", "/about.html", "/services.html", "/gallery.html", "/testimonials.html", "/faq.html", "/book-us.html"]
    body = "".join(f"<url><loc>{settings['site_url']}{u}</loc></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'
    return Response(content=xml, media_type="application/xml")
