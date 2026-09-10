"""The admin panel's Gallery section — full CRUD for the GalleryItem
table, same list/new/create/edit/delete shape as services.py, plus real
file-upload handling for the photo itself (the one content type that
involves a binary upload rather than just text fields).

Uploaded files are saved to local disk under images/uploads/, which is
backed by a persistent Railway volume (mounted at /app/images/uploads —
see .railway/railway.py) specifically so this survives redeploys; Railway's
container filesystem is otherwise ephemeral and a plain upload would
silently vanish on the very next deploy (this happened once, before the
volume existed — see the git history around when it was added).

Videos can be either a link (YouTube, Vimeo, Facebook, Instagram, TikTok,
or a direct video file hosted elsewhere — see app/content.py's
_analyze_video_url) or an uploaded video file, saved the same way photos
are (see _save_video_upload) now that the volume makes that safe. A
direct upload is capped at MAX_VIDEO_UPLOAD_BYTES — video files are much
larger than photos, and the volume, while persistent, isn't unlimited.
The `photo` field is still accepted for a video row either way, reused as
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
VIDEO_UPLOAD_DIR = UPLOAD_DIR / "videos"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov"}
MAX_VIDEO_UPLOAD_BYTES = 100 * 1024 * 1024  # 100MB
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


def _save_video_upload(file: UploadFile | None) -> tuple[str | None, str | None]:
    """Saves an uploaded video file to disk, same persistent volume as
    photo uploads (see this module's docstring). Returns (path, error) —
    exactly one is ever set. Unlike a poster photo, a bad video upload
    can't just be silently skipped (the video itself is the whole point
    of the form submission), so a wrong extension or an over-limit file
    comes back as an error the caller re-renders the form with, rather
    than quietly saving nothing.

    Streamed to disk in 1MB chunks rather than file.file.read() in one
    shot, so a 100MB upload doesn't sit fully buffered in memory at once;
    aborted (and the partial file deleted) the moment it crosses
    MAX_VIDEO_UPLOAD_BYTES, rather than after writing the whole thing."""
    if file is None or not file.filename:
        return None, None
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        return None, f"'{ext}' isn't a supported video format — use one of: {allowed}."
    VIDEO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = VIDEO_UPLOAD_DIR / filename
    written = 0
    try:
        with open(dest, "wb") as out:
            while chunk := file.file.read(1024 * 1024):
                written += len(chunk)
                if written > MAX_VIDEO_UPLOAD_BYTES:
                    raise ValueError("video file too large")
                out.write(chunk)
    except ValueError:
        dest.unlink(missing_ok=True)
        limit_mb = MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024)
        return None, f"That video is over the {limit_mb}MB limit — trim it, or host it elsewhere and paste the link instead."
    return f"/images/uploads/videos/{filename}", None


def _resolve_video_source(
    media_type: str, video_url: str, video_file: UploadFile | None, keep_existing: str | None
) -> tuple[str | None, str | None]:
    """Decides what to actually store in GalleryItem.video_url from the
    three ways a video row's source can come in, in priority order:
    1. An uploaded file, if one was chosen — takes priority since
       choosing a new file is the most deliberate possible action.
    2. The Video URL text field, if non-empty (resolving any TikTok short
       link first — see _resolve_short_link).
    3. `keep_existing` — the item's current video_url, so an edit that
       touches neither field doesn't wipe it. None on create, since
       there's nothing to keep yet. (The text field is always pre-filled
       with the current value on the edit form, so in practice case 2
       already covers "unchanged" — this is a defensive fallback in case
       it's ever missing, e.g. a future template change.)
    Returns (video_url, error) — exactly one is set; an error means the
    upload failed validation and the caller should re-render the form
    with it rather than saving.
    """
    if media_type != "video":
        return None, None
    if video_file is not None and video_file.filename:
        path, error = _save_video_upload(video_file)
        if error:
            return None, error
        return path, None
    if video_url.strip():
        return _resolve_short_link(video_url.strip()), None
    return keep_existing, None


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
        {
            "title": "Add Photo or Video",
            "active": "gallery",
            "item": None,
            "categories": CATEGORIES,
            "media_types": MEDIA_TYPES,
            "max_video_mb": MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024),
        },
    )


@router.post("/new")
def create_gallery_item(
    request: Request,
    label: str = Form(...),
    category: str = Form(...),
    order: int = Form(1),
    media_type: str = Form("image"),
    video_url: str = Form(""),
    is_hero: str | None = Form(None),
    photo: UploadFile | None = None,
    video_file: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    """Handles the add form submit. `photo` is optional either way —
    for an image row it's the photo itself (placeholder icon until
    uploaded); for a video row it's an optional poster. The video itself
    comes from either `video_url` or `video_file` — see
    _resolve_video_source for the priority between them."""
    if media_type not in MEDIA_TYPES:
        media_type = "image"
    resolved_video_url, error = _resolve_video_source(media_type, video_url, video_file, keep_existing=None)
    if error:
        return templates.TemplateResponse(
            request,
            "admin/gallery_form.html",
            {
                "title": "Add Photo or Video",
                "active": "gallery",
                "item": None,
                "categories": CATEGORIES,
                "media_types": MEDIA_TYPES,
                "max_video_mb": MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024),
                "error": error,
            },
            status_code=422,
        )
    image_path = _save_upload(photo) or ""
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
        {
            "title": "Edit Photo or Video",
            "active": "gallery",
            "item": item,
            "categories": CATEGORIES,
            "media_types": MEDIA_TYPES,
            "max_video_mb": MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024),
        },
    )


@router.post("/{item_id}/edit")
def update_gallery_item(
    item_id: int,
    request: Request,
    label: str = Form(...),
    category: str = Form(...),
    order: int = Form(1),
    media_type: str = Form("image"),
    video_url: str = Form(""),
    is_hero: str | None = Form(None),
    photo: UploadFile | None = None,
    video_file: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    """Handles the edit form's submit. Uploading a new photo/poster
    replaces the old one; leaving the file field empty keeps whatever's
    already stored, since _save_upload returns None when nothing was
    chosen. The video itself comes from either `video_url` or
    `video_file` — see _resolve_video_source for the priority between
    them, including how an edit that touches neither keeps the current
    video_url rather than wiping it."""
    if media_type not in MEDIA_TYPES:
        media_type = "image"
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    if not item:
        return RedirectResponse(url="/gallery", status_code=303)
    resolved_video_url, error = _resolve_video_source(media_type, video_url, video_file, keep_existing=item.video_url)
    if error:
        return templates.TemplateResponse(
            request,
            "admin/gallery_form.html",
            {
                "title": "Edit Photo or Video",
                "active": "gallery",
                "item": item,
                "categories": CATEGORIES,
                "media_types": MEDIA_TYPES,
                "max_video_mb": MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024),
                "error": error,
            },
            status_code=422,
        )
    item.label = label
    item.category = category
    item.order = order
    item.media_type = media_type
    item.video_url = resolved_video_url
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
