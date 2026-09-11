"""The admin panel's landing page (GET / on the admin hostname) — a
dashboard showing how many rows are in each table, linking to each
section. Purely a summary view; all the actual management happens in the
other routers (bookings.py, services.py, etc.).
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from ... import backup, storage
from ...database import get_db
from ...models import Booking, BookingStatus, FAQItem, GalleryItem, Service, Testimonial
from ...asset_version import ASSET_VERSION
from ...security import require_admin

# `dependencies=[Depends(require_admin)]` at the router level applies the
# login check to every route in this router — same pattern used by every
# other router under app/admin/routers/.
router = APIRouter(tags=["home"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))
templates.env.globals["asset_version"] = ASSET_VERSION


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
    backups = backup.list_backups()
    last_backup_at = None
    if backups:
        # Keys look like "backups/2026-09-11T00-00-00Z.json.gz" — see
        # app/backup.py:run_backup for exactly how the timestamp is formatted.
        raw_timestamp = backups[-1].removeprefix(backup.BACKUP_PREFIX).removesuffix(".json.gz")
        try:
            last_backup_at = datetime.strptime(raw_timestamp, "%Y-%m-%dT%H-%M-%SZ")
        except ValueError:
            last_backup_at = None
    backup_status = {
        "configured": storage.bucket_configured(),
        "count": len(backups),
        "last_backup_at": last_backup_at,
    }
    return templates.TemplateResponse(
        request,
        "admin/home.html",
        {"title": "Dashboard", "active": "home", "counts": counts, "backup_status": backup_status},
    )
