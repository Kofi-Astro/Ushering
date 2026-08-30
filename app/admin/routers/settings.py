"""The admin panel's Site Settings section — a single edit form (no
list/new/delete, unlike the other content routers) for the one-row
SiteSetting table: contact info, social links, and branding text used
throughout the public site's templates.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import SiteSetting
from ...security import require_admin

router = APIRouter(prefix="/settings", tags=["settings-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


def _get_or_create(db: Session) -> SiteSetting:
    """Fetches the single settings row (id=1), creating it with its model
    defaults first if it somehow doesn't exist yet (normally app/seed.py
    already created it on first startup, but this is a safety net so the
    settings form never 500s on a fresh/unusual database)."""
    row = db.query(SiteSetting).filter(SiteSetting.id == 1).first()
    if row is None:
        row = SiteSetting(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("")
def settings_form(request: Request, saved: bool = False, db: Session = Depends(get_db)):
    """Renders the settings form pre-filled with current values. The
    `?saved=1` query param (added by update_settings's redirect below)
    shows a brief confirmation message after a successful save."""
    settings_row = _get_or_create(db)
    return templates.TemplateResponse(
        request,
        "admin/settings_form.html",
        {
            "title": "Site Settings",
            "active": "settings",
            "settings": settings_row,
            "message": "Settings saved." if saved else None,
        },
    )


@router.post("")
def update_settings(
    site_name: str = Form(...),
    site_url: str = Form(...),
    tagline: str = Form(...),
    phone_display: str = Form(...),
    whatsapp_number: str = Form(...),
    email: str = Form(...),
    address: str = Form(...),
    facebook_url: str = Form(""),
    instagram_url: str = Form(""),
    tiktok_url: str = Form(""),
    db: Session = Depends(get_db),
):
    """Handles the settings form's submit — overwrites every field on the
    single settings row. Social link fields default to "#" if left blank,
    since the templates always render a link element for them regardless
    (an empty href would be worse than a harmless "#")."""
    row = _get_or_create(db)
    row.site_name = site_name
    row.site_url = site_url.rstrip("/")  # avoid a trailing "//" when other code appends a path
    row.tagline = tagline
    row.phone_display = phone_display
    row.whatsapp_number = whatsapp_number
    row.email = email
    row.address = address
    row.facebook_url = facebook_url or "#"
    row.instagram_url = instagram_url or "#"
    row.tiktok_url = tiktok_url or "#"
    db.commit()
    return RedirectResponse(url="/settings?saved=1", status_code=303)
