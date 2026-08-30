from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Booking, BookingStatus, FAQItem, GalleryItem, Service, Testimonial
from ...security import require_admin

router = APIRouter(tags=["home"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("/")
def dashboard_home(request: Request, db: Session = Depends(get_db)):
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
