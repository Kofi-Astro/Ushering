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

Videos can be a link (YouTube, Vimeo, Facebook, Instagram, TikTok, or a
direct video file hosted elsewhere — see app/content.py's
_analyze_video_url) or an uploaded video file. An uploaded video goes
straight to the Railway Bucket (see app/storage.py) via a presigned
direct browser-to-bucket upload — gallery_form.html's JS asks this
router for a presigned URL (see get_video_upload_url below) and PUTs the
file there itself, so the video's bytes never pass through this app's
own request handling at all. That's deliberate: routing a large video
through this app server — even just to write it to the volume — was
tripping some upstream size/rate protection the business owner ran into
("too big" / "overload-protect" errors). If no bucket is configured
(bucket_configured() is False — e.g. local dev), the form's JS falls
back to _save_video_upload below instead, which writes to the same
local-disk volume photos use, capped at MAX_VIDEO_UPLOAD_BYTES since
that path doesn't have a bucket's effectively unlimited storage. The
`photo` field is accepted for a video row either way, reused as an
optional poster/thumbnail image rather than the video itself — and if
it's left empty, one is fetched automatically for a link-based video
(see _fetch_remote_poster) via each platform's own public oEmbed
endpoint (Vimeo, TikTok) or its Open Graph preview image (Facebook,
Instagram); only a genuinely unrecognized link falls back to the plain
icon with no poster at all.
"""

import json
import re
import urllib.request
import uuid
from html import unescape
from pathlib import Path
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ... import storage
from ...content import _analyze_video_url, _FACEBOOK_VIDEO_RE, _INSTAGRAM_RE, _TIKTOK_RE, _VIMEO_RE
from ...database import get_db
from ...models import GalleryItem
from ...asset_version import ASSET_VERSION
from ...security import require_admin

router = APIRouter(prefix="/gallery", tags=["gallery-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))
templates.env.globals["asset_version"] = ASSET_VERSION

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


# Meta's own documented crawler UA — the one Facebook/Messenger/WhatsApp
# themselves send when generating a link-preview card for a shared URL.
# Sending it here isn't circumventing anything: it's the exact, sanctioned
# way to ask Facebook/Instagram for a page's preview image, which is all
# _og_image below does. A generic browser UA gets a stripped-down,
# tag-free response from both (confirmed directly) — this one doesn't.
_CRAWLER_USER_AGENT = "facebookexternalhit/1.1"
_OG_IMAGE_RE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']')


def _oembed_thumbnail(oembed_url: str) -> str | None:
    """Vimeo and TikTok both expose a public, no-auth-required oEmbed
    endpoint that includes a real thumbnail_url — unlike Facebook and
    Instagram, neither requires a developer app/access token for this."""
    try:
        request = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
        return data.get("thumbnail_url") or None
    except Exception:
        return None


def _og_image(page_url: str) -> str | None:
    """Scrapes the Open Graph image tag off a Facebook/Instagram post's
    own page — neither offers a public oEmbed endpoint (both now require
    a Meta developer app), but both still render an og:image tag for
    link-preview purposes, given the right (see _CRAWLER_USER_AGENT)
    User-Agent. Reads at most 300KB rather than the whole page — the tag
    is always in the <head>, and these pages can run into the megabytes."""
    try:
        request = urllib.request.Request(page_url, headers={"User-Agent": _CRAWLER_USER_AGENT})
        with urllib.request.urlopen(request, timeout=6) as response:
            html = response.read(300_000).decode("utf-8", errors="replace")
        match = _OG_IMAGE_RE.search(html)
        return unescape(match.group(1)) if match else None
    except Exception:
        return None


def _download_image(image_url: str) -> tuple[bytes | None, str]:
    """Downloads a poster image found by one of the functions above.
    Capped at 10MB (thumbnails are never anywhere near that) so a
    misbehaving response can't tie up the request indefinitely."""
    try:
        request = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(10 * 1024 * 1024)
        ext = ".jpg"
        if "png" in content_type:
            ext = ".png"
        elif "webp" in content_type:
            ext = ".webp"
        elif "gif" in content_type:
            ext = ".gif"
        return data, ext
    except Exception:
        return None, ".jpg"


def _fetch_remote_poster(video_url: str) -> str | None:
    """Best-effort automatic poster for a video added by link rather than
    upload. YouTube already gets a real thumbnail for free (a predictable
    URL — see app/content.py's _analyze_video_url), no request needed;
    this covers the other four platforms, each saved to disk the same way
    a manually-uploaded poster would be (rather than storing the remote
    URL directly, which the platform could later move or delete).

    Only ever called at save time (see create/update_gallery_item below),
    never from the read path — this can make a real network call, and
    app/content.py's read functions are deliberately network-free. Never
    raises; on any failure this returns None and the item just falls back
    to the generic icon, exactly like before this existed."""
    thumbnail_url = None
    if _VIMEO_RE.search(video_url):
        thumbnail_url = _oembed_thumbnail(f"https://vimeo.com/api/oembed.json?url={quote(video_url, safe='')}")
    elif _TIKTOK_RE.search(video_url):
        thumbnail_url = _oembed_thumbnail(f"https://www.tiktok.com/oembed?url={quote(video_url, safe='')}")
    elif _INSTAGRAM_RE.search(video_url) or _FACEBOOK_VIDEO_RE.search(video_url):
        thumbnail_url = _og_image(video_url)
    if not thumbnail_url:
        return None
    data, ext = _download_image(thumbnail_url)
    if not data:
        return None
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(UPLOAD_DIR / filename, "wb") as out:
        out.write(data)
    return f"/images/uploads/{filename}"


@router.get("/video-upload-url")
def get_video_upload_url(filename: str, content_type: str = "video/mp4"):
    """Returns a presigned URL the admin's browser PUTs a video file to
    directly (see app/storage.py) — called by gallery_form.html's JS
    before the rest of the form submits. 404s if no bucket is configured
    (app/storage.py:bucket_configured), so the form's JS knows to fall
    back to submitting the file through the form itself instead (see
    _save_video_upload)."""
    if not storage.bucket_configured():
        raise HTTPException(status_code=404, detail="No bucket configured")
    key = storage.new_video_key(filename)
    return {"upload_url": storage.generate_upload_url(key, content_type), "key": key}


def _resolve_video_source(
    media_type: str,
    video_url: str,
    video_file: UploadFile | None,
    video_object_key: str,
    keep_existing: str | None,
) -> tuple[str | None, str | None]:
    """Decides what to actually store in GalleryItem.video_url from the
    four ways a video row's source can come in, in priority order:
    1. `video_object_key` — set by gallery_form.html's JS after it
       finished a direct browser-to-bucket upload (see
       get_video_upload_url above). Stored with storage.KEY_PREFIX so
       app/content.py's _analyze_video_url can recognize it later.
    2. An uploaded file the OLD way, if one was chosen — only reached
       when no bucket is configured, so the form's JS fell back to
       letting the file ride along with the rest of the form (see
       _save_video_upload).
    3. The Video URL text field, if non-empty (resolving any TikTok short
       link first — see _resolve_short_link).
    4. `keep_existing` — the item's current video_url, so an edit that
       touches none of the above doesn't wipe it. None on create, since
       there's nothing to keep yet.
    Returns (video_url, error) — exactly one is set; an error means the
    upload failed validation and the caller should re-render the form
    with it rather than saving.
    """
    if media_type != "video":
        return None, None
    if video_object_key.strip():
        return f"{storage.KEY_PREFIX}{video_object_key.strip()}", None
    if video_file is not None and video_file.filename:
        path, error = _save_video_upload(video_file)
        if error:
            return None, error
        return path, None
    if video_url.strip():
        return _resolve_short_link(video_url.strip()), None
    return keep_existing, None


def _delete_if_bucket_video(video_url: str | None) -> None:
    """Cleans up the bucket object behind a video_url, if it is one (see
    storage.KEY_PREFIX) — called whenever a GalleryItem's video is
    deleted or replaced, so bucket storage doesn't silently accumulate
    orphaned files the local-disk uploads already do (see
    delete_gallery_item's docstring for why that one's left as-is)."""
    if video_url and video_url.startswith(storage.KEY_PREFIX):
        storage.delete_video(video_url[len(storage.KEY_PREFIX):])


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
            "bucket_configured": storage.bucket_configured(),
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
    video_object_key: str = Form(""),
    is_hero: str | None = Form(None),
    photo: UploadFile | None = None,
    video_file: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    """Handles the add form submit. `photo` is optional either way —
    for an image row it's the photo itself (placeholder icon until
    uploaded); for a video row it's an optional poster. The video itself
    comes from `video_object_key`, `video_file` or `video_url` — see
    _resolve_video_source for the priority between them."""
    if media_type not in MEDIA_TYPES:
        media_type = "image"
    resolved_video_url, error = _resolve_video_source(
        media_type, video_url, video_file, video_object_key, keep_existing=None
    )
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
                "bucket_configured": storage.bucket_configured(),
                "error": error,
            },
            status_code=422,
        )
    image_path = _save_upload(photo) or ""
    if media_type == "video" and not image_path and resolved_video_url:
        image_path = _fetch_remote_poster(resolved_video_url) or ""
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
            "bucket_configured": storage.bucket_configured(),
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
    video_object_key: str = Form(""),
    is_hero: str | None = Form(None),
    photo: UploadFile | None = None,
    video_file: UploadFile | None = None,
    db: Session = Depends(get_db),
):
    """Handles the edit form's submit. Uploading a new photo/poster
    replaces the old one; leaving the file field empty keeps whatever's
    already stored, since _save_upload returns None when nothing was
    chosen. The video itself comes from `video_object_key`, `video_file`
    or `video_url` — see _resolve_video_source for the priority between
    them, including how an edit that touches none of them keeps the
    current video_url rather than wiping it. If the video is actually
    changing and the old one lived in the bucket, it's deleted there too
    (see _delete_if_bucket_video) rather than left orphaned."""
    if media_type not in MEDIA_TYPES:
        media_type = "image"
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    if not item:
        return RedirectResponse(url="/gallery", status_code=303)
    resolved_video_url, error = _resolve_video_source(
        media_type, video_url, video_file, video_object_key, keep_existing=item.video_url
    )
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
                "bucket_configured": storage.bucket_configured(),
                "error": error,
            },
            status_code=422,
        )
    if resolved_video_url != item.video_url:
        _delete_if_bucket_video(item.video_url)
    item.label = label
    item.category = category
    item.order = order
    item.media_type = media_type
    item.video_url = resolved_video_url
    item.is_hero = bool(is_hero) if media_type == "video" else False
    new_image = _save_upload(photo)
    if new_image:
        item.image = new_image
    elif media_type == "video" and not item.image and resolved_video_url:
        # Only fills a genuinely missing poster — never overwrites one
        # that's already there, whether it was uploaded manually or by
        # this same auto-fetch on an earlier save. Lets an admin "heal" an
        # existing video that predates this feature just by opening its
        # edit page and saving again, with nothing else needing to change.
        item.image = _fetch_remote_poster(resolved_video_url) or item.image
    db.commit()
    return RedirectResponse(url="/gallery", status_code=303)


@router.post("/{item_id}/delete")
def delete_gallery_item(item_id: int, db: Session = Depends(get_db)):
    """Removes the database row. Note: this does NOT delete an uploaded
    photo/local-disk video file itself from images/uploads/ — it's simply
    left orphaned on disk, fine at this scale. A bucket-stored video (see
    _delete_if_bucket_video) is deleted for real, though — unlike the
    volume's fixed allocation, bucket storage has a real ongoing cost per
    GB kept around."""
    item = db.query(GalleryItem).filter(GalleryItem.id == item_id).first()
    if item:
        _delete_if_bucket_video(item.video_url)
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/gallery", status_code=303)
