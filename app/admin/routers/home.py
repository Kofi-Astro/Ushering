"""The admin panel's landing page (GET / on the admin hostname) — a
dashboard showing how many rows are in each table, linking to each
section. Purely a summary view; all the actual management happens in the
other routers (bookings.py, services.py, etc.).
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Booking, BookingStatus, FAQItem, GalleryItem, Service, Testimonial
from ...security import require_admin

# `dependencies=[Depends(require_admin)]` at the router level applies the
# login check to every route in this router — same pattern used by every
# other router under app/admin/routers/.
router = APIRouter(tags=["home"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("/")
def dashboard_home(request: Request, db: Session = Depends(get_db)):
    """Runs a handful of cheap COUNT queries (one per table) and hands
    them to the template as simple numbers — no need to load full rows
    just to show "9 services, 6 testimonials" etc."""
    new_bookings = db.query(func.count(Booking.id)).filter(Booking.status == BookingStatus.new).scalar() or 0
    counts = {
        "bookings": db.query(func.count(Booking.id)).scalar() or 0,
        "new_bookings": new_bookings,
        "services": db.query(func.count(Service.id)).scalar() or 0,
        "testimonials": db.query(func.count(Testimonial.id)).scalar() or 0,
        "gallery": db.query(func.count(GalleryItem.id)).scalar() or 0,
        "faq": db.query(func.count(FAQItem.id)).scalar() or 0,
    }
    return templates.TemplateResponse(
        request,
        "admin/home.html",
        {"title": "Dashboard", "active": "home", "counts": counts},
    )
