"""The admin panel's Gallery section — full CRUD for the GalleryItem
table, same list/new/create/edit/delete shape as services.py, plus real
file-upload handling for the photo itself (the one content type that
involves a binary upload rather than just text fields).

NOTE (see docs/technical-overview.html's deployment callout): uploaded
files are saved to local disk under images/uploads/. That's fine for
local dev, but Railway's default filesystem is ephemeral — a redeploy can
wipe it. Attach a Railway volume mounted at images/uploads/, or move this
to object storage (e.g. Cloudflare R2), before relying on this in
production.

Videos are handled differently: by URL only (YouTube, Vimeo, Facebook,
Instagram, TikTok, or a direct video file hosted elsewhere), never by
uploading a video file through this form. Video files are typically far
larger than photos, and the same ephemeral-disk caveat above would turn
into a much bigger problem — filling the disk fast and losing the
"upload" on the next redeploy. The
`photo` file field is still accepted for a video row, but it's reused as
an optional poster/thumbnail image rather than the video itself.
"""

import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...content import _analyze_video_url
from ...database import get_db
from ...models import GalleryItem
from ...security import require_admin

router = APIRouter(prefix="/gallery", tags=["gallery-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))

# Repo root's images/uploads/ — four .parent calls from this file
# (routers/ -> admin/ -> app/ -> repo root), then down into images/uploads.
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "images" / "uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
CATEGORIES = ["weddings", "corporate", "funerals", "conferences", "parties"]
MEDIA_TYPES = ["image", "video"]

# TikTok's mobile share sheet ("Copy Link") gives a vt.tiktok.com/
# vm.tiktok.com short link — a pure redirect with no video ID anywhere in
# it, unlike the @user/video/<id> form app/content.py:_analyze_video_url
# knows how to embed. Resolved once, here, at save time (see
# _resolve_short_link below) rather than every time the video is
# displayed — content.py's read path is deliberately network-free, so a
# short link saved without ever going through this form (e.g. inserted
# directly into the database) would just silently not embed, same as
# before this existed.
_SHORT_LINK_HOSTS = {"vt.tiktok.com", "vm.tiktok.com"}


def _resolve_short_link(url: str) -> str:
    """Follows a TikTok short link's redirect to the canonical URL
    _analyze_video_url can actually recognize. Falls back to the URL
    exactly as entered if anything goes wrong (offline, TikTok
    unreachable, unexpected response, timeout) — the save still succeeds
    either way, the video just won't embed until it's re-saved with a
    working link, exactly like today's behavior for any unrecognized URL."""
    if urlparse(url).hostname not in _SHORT_LINK_HOSTS:
        return url
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.geturl()
    except Exception:
        return url


def _save_upload(file: UploadFile | None) -> str | None:
    """Saves an uploaded photo to disk under a random filename (so two
    people uploading files called "photo.jpg" never collide) and returns
    the public URL path to store in GalleryItem.image. Returns None if no
    file was actually chosen, or if its extension isn't one of the
    allowed image types — callers treat None as "nothing to update"."""
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
    """The /gallery landing page: every photo tile (or placeholder icon,
    for entries with no image yet), in display order. Each video's
    video_url is run through the exact same classifier the public site
    uses (app/content.py:_analyze_video_url) so a link that won't
    actually embed — an unsupported platform, a malformed URL, a TikTok
    short link that failed to resolve — shows a clear warning here
    instead of silently doing nothing on the live site."""
    items = db.query(GalleryItem).order_by(GalleryItem.order).all()
    unplayable_ids = set()
    for item in items:
        if item.media_type != "video" or not item.video_url:
            continue
        classified = _analyze_video_url(item.video_url)
        if not classified["direct_src"] and not classified["embed_url"] and not classified["external_url"]:
            unplayable_ids.add(item.id)
    return templates.TemplateResponse(
        request,
        "admin/gallery_list.html",
        {"title": "Gallery", "active": "gallery", "items": items, "unplayable_ids": unplayable_ids},
    )


@router.get("/new")
def new_gallery_form(request: Request):
    """Blank add-photo/video form. `categories`/`media_types` are passed
    in so the template can render both <select>s without hardcoding
    either list twice."""
    return templates.TemplateResponse(
        request,
        "admin/gallery_form.html",
        {"title": "Add Photo or Video", "active": "gallery", "item": None, "categories": CATEGORIES, "media_types": MEDIA_TYPES},
    )


@router.post("/new")
def create_gallery_item(
    label: str = Form(...),
    category: str = Form(...),
    order: int = Form(1),
    media_type: str = Form("image"),
    video_url: str = Form(""),
    is_hero: str | None = Form(None),
    photo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    """Handles the add form submit. `photo` is optional either way —
    for an image row it's the photo itself (placeholder icon until
    uploaded); for a video row it's an optional poster (see this file's
    module docstring for why video itself is URL-only)."""
    if media_type not in MEDIA_TYPES:
        media_type = "image"
    image_path = _save_upload(photo) or ""
    resolved_video_url = _resolve_short_link(video_url.strip()) if media_type == "video" and video_url.strip() else None
    db.add(
        GalleryItem(
            label=label,
            category=category,
            order=order,
            image=image_path,
            media_type=media_type,
            video_url=resolved_video_url,
            is_hero=bool(is_hero) if media_type == "video" else False,
        )
    )
    db.commit()
    return RedirectResponse(url="/gallery", status_code=303)


@router.get("/{item_id}/edit")
def edit_gallery_form(item_id: int, request: Request, db: Session = Depends(get_db)):
    """Pre-filled edit form; also shows a preview of the current photo, if
    any (see admin/gallery_form.html's "current-image" block)."""
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    return templates.TemplateResponse(
        request,
        "admin/gallery_form.html",
        {"title": "Edit Photo or Video", "active": "gallery", "item": item, "categories": CATEGORIES, "media_types": MEDIA_TYPES},
    )


@router.post("/{item_id}/edit")
def update_gallery_item(
    item_id: int,
    label: str = Form(...),
    category: str = Form(...),
    order: int = Form(1),
    media_type: str = Form("image"),
    video_url: str = Form(""),
    is_hero: str | None = Form(None),
    photo: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    """Handles the edit form's submit. Uploading a new photo/poster
    replaces the old one; leaving the file field empty keeps whatever's
    already stored, since _save_upload returns None when nothing was
    chosen."""
    if media_type not in MEDIA_TYPES:
        media_type = "image"
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    if item:
        item.label = label
        item.category = category
        item.order = order
        item.media_type = media_type
        item.video_url = (
            _resolve_short_link(video_url.strip()) if media_type == "video" and video_url.strip() else None
        )
        item.is_hero = bool(is_hero) if media_type == "video" else False
        new_image = _save_upload(photo)
        if new_image:
            item.image = new_image
        db.commit()
    return RedirectResponse(url="/gallery", status_code=303)


@router.post("/{item_id}/delete")
def delete_gallery_item(item_id: int, db: Session = Depends(get_db)):
    """Removes the database row. Note: this does NOT delete the uploaded
    file itself from images/uploads/ — it's simply left orphaned on disk.
    Fine at this scale; worth cleaning up if storage ever becomes a
    concern."""
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/gallery", status_code=303)
