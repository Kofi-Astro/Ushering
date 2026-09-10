"""The admin panel's Team Photos section — full CRUD for the small
carousel of photos shown in the "Who We Are" (Home) / "Our Story" (About)
spot, a deliberately separate and simpler section from Gallery: just a
photo, an optional caption, and a display order — no categories, no
video. See app/models.py:TeamPhoto for why this exists as its own table
instead of being pulled from Gallery automatically.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import TeamPhoto
from ...security import require_admin

router = APIRouter(prefix="/team-photos", tags=["team-photos-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))

# Same physical directory (and Railway volume) as Gallery's photo uploads
# — see app/admin/routers/gallery.py's UPLOAD_DIR comment.
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "images" / "uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _save_upload(file: UploadFile | None) -> str | None:
    """Identical logic to gallery.py's _save_upload — kept as its own copy
    rather than a shared import since the two sections are deliberately
    independent and a future change to one (e.g. Gallery growing a size
    limit) shouldn't silently also change the other."""
    if file is None or not file.filename:
        return None
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(UPLOAD_DIR / filename, "wb") as out:
        out.write(file.file.read())
    return f"/images/uploads/{filename}"


@router.get("")
def list_team_photos(request: Request, db: Session = Depends(get_db)):
    items = db.query(TeamPhoto).order_by(TeamPhoto.order).all()
    return templates.TemplateResponse(
        request, "admin/team_photos_list.html", {"title": "Team Photos", "active": "team_photos", "items": items}
    )


@router.get("/new")
def new_team_photo_form(request: Request):
    return templates.TemplateResponse(
        request, "admin/team_photo_form.html", {"title": "Add Team Photo", "active": "team_photos", "item": None}
    )


@router.post("/new")
def create_team_photo(
    request: Request,
    caption: str = Form(""),
    order: int = Form(1),
    photo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    image_path = _save_upload(photo)
    if not image_path:
        return templates.TemplateResponse(
            request,
            "admin/team_photo_form.html",
            {
                "title": "Add Team Photo",
                "active": "team_photos",
                "item": None,
                "error": "Please choose a JPG, PNG, WebP or GIF photo.",
            },
            status_code=422,
        )
    db.add(TeamPhoto(image=image_path, caption=caption, order=order))
    db.commit()
    return RedirectResponse(url="/team-photos", status_code=303)


@router.get("/{item_id}/edit")
def edit_team_photo_form(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(TeamPhoto).filter(TeamPhoto.id == item_id).first()
    return templates.TemplateResponse(
        request, "admin/team_photo_form.html", {"title": "Edit Team Photo", "active": "team_photos", "item": item}
    )


@router.post("/{item_id}/edit")
def update_team_photo(
    item_id: int,
    caption: str = Form(""),
    order: int = Form(1),
    photo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    item = db.query(TeamPhoto).filter(TeamPhoto.id == item_id).first()
    if item:
        item.caption = caption
        item.order = order
        new_image = _save_upload(photo)
        if new_image:
            item.image = new_image
        db.commit()
    return RedirectResponse(url="/team-photos", status_code=303)


@router.post("/{item_id}/delete")
def delete_team_photo(item_id: int, db: Session = Depends(get_db)):
    item = db.query(TeamPhoto).filter(TeamPhoto.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/team-photos", status_code=303)
