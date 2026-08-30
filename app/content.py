"""Read-side helpers for the site's editable content — services, gallery,
testimonials, FAQ and site-wide settings. All of it lives in the database
now (see app/models.py) and is edited through the admin panel at
/services, /gallery, /testimonials, /faq and /settings. This module is
just the shape-conversion layer between the DB rows and what the public
page templates expect (kept stable so app/routers/pages.py and the
templates under app/templates/pages/ didn't need to change).
"""

import markdown as md

from .database import SessionLocal
from .models import FAQItem, GalleryItem, Service, SiteSetting, Testimonial


def get_services() -> list[dict]:
    with SessionLocal() as db:
        rows = db.query(Service).order_by(Service.order).all()
        return [
            {
                "id": s.id,
                "title": s.title,
                "icon": s.icon,
                "order": s.order,
                "homeDescription": s.home_description,
                "description": s.description,
                "highlights": [line.strip() for line in s.highlights.splitlines() if line.strip()],
            }
            for s in rows
        ]


def get_testimonials() -> list[dict]:
    with SessionLocal() as db:
        rows = db.query(Testimonial).order_by(Testimonial.order).all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "role": t.role,
                "rating": t.rating,
                "order": t.order,
                "body_html": md.markdown(t.quote.strip()) if t.quote else "",
            }
            for t in rows
        ]


def get_gallery_items() -> list[dict]:
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


def get_site_settings() -> dict:
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
        }
