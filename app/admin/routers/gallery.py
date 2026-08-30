import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import GalleryItem
from ...security import require_admin

router = APIRouter(prefix="/gallery", tags=["gallery-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "images" / "uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
CATEGORIES = ["weddings", "corporate", "funerals", "conferences", "parties"]


def _save_upload(file: UploadFile | None) -> str | None:
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
def list_gallery(request: Request, db: Session = Depends(get_db)):
    items = db.query(GalleryItem).order_by(GalleryItem.order).all()
    return templates.TemplateResponse(
        request, "admin/gallery_list.html", {"title": "Gallery", "active": "gallery", "items": items}
    )


@router.get("/new")
def new_gallery_form(request: Request):
    return templates.TemplateResponse(
        request,
        "admin/gallery_form.html",
        {"title": "Add Photo", "active": "gallery", "item": None, "categories": CATEGORIES},
    )


@router.post("/new")
def create_gallery_item(
    label: str = Form(...),
    category: str = Form(...),
    order: int = Form(1),
    photo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    image_path = _save_upload(photo) or ""
    db.add(GalleryItem(label=label, category=category, order=order, image=image_path))
    db.commit()
    return RedirectResponse(url="/gallery", status_code=303)


@router.get("/{item_id}/edit")
def edit_gallery_form(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    return templates.TemplateResponse(
        request,
        "admin/gallery_form.html",
        {"title": "Edit Photo", "active": "gallery", "item": item, "categories": CATEGORIES},
    )


@router.post("/{item_id}/edit")
def update_gallery_item(
    item_id: int,
    label: str = Form(...),
    category: str = Form(...),
    order: int = Form(1),
    photo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    if item:
        item.label = label
        item.category = category
        item.order = order
        new_image = _save_upload(photo)
        if new_image:
            item.image = new_image
        db.commit()
    return RedirectResponse(url="/gallery", status_code=303)


@router.post("/{item_id}/delete")
def delete_gallery_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/gallery", status_code=303)
