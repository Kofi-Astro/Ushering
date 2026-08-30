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
    row = db.query(SiteSetting).filter(SiteSetting.id == 1).first()
    if row is None:
        row = SiteSetting(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("")
def settings_form(request: Request, saved: bool = False, db: Session = Depends(get_db)):
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
    row = _get_or_create(db)
    row.site_name = site_name
    row.site_url = site_url.rstrip("/")
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
