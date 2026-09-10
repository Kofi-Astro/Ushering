"""S3-compatible object storage for uploaded video files (a Railway
Bucket — see `railway bucket` in the CLI, and app/config.py's bucket_*
settings). Photos still go through the local-disk + persistent-volume
path in app/admin/routers/gallery.py — this exists specifically for
video, which is large enough that routing it through this app's own
request handling (even just to write it to the volume) tripped some
upstream size/rate protection the business owner ran into ("too big" /
"overload-protect" errors).

The actual video bytes never pass through this app's own server at all:
the admin's browser uploads directly to the bucket using a presigned PUT
URL this module generates (see generate_upload_url), and the object is
served back to visitors via a presigned GET URL (see
generate_playback_url) rather than a public bucket URL — this provider
doesn't guarantee public-read buckets are configurable, so a fresh
presigned URL is generated on every page render instead, the same
"nothing here is cached, always read fresh" pattern app/content.py
already uses for everything else.
"""

import uuid
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.client import Config

from .config import get_settings

# Playback URLs are regenerated fresh on every page render (see
# app/content.py's _analyze_video_url), so this only needs to outlive a
# single visitor's page view comfortably — not indefinitely.
PLAYBACK_URL_EXPIRY_SECONDS = 6 * 60 * 60  # 6 hours
UPLOAD_URL_EXPIRY_SECONDS = 15 * 60  # 15 minutes — plenty for an upload to start

# Prefixes a bucket object key when stored in GalleryItem.video_url, so
# app/content.py's _analyze_video_url can tell "this is our own bucket
# object" apart from an external link or a local /images/uploads/ path
# at a glance, with no extra database column needed.
KEY_PREFIX = "bucket:"


def bucket_configured() -> bool:
    """Whether the bucket environment variables are actually set — lets
    callers show a clear "not set up yet" message instead of boto3
    raising a confusing exception when they're blank (e.g. local dev, or
    before `railway bucket create` has been run)."""
    settings = get_settings()
    return bool(
        settings.bucket_endpoint
        and settings.bucket_access_key_id
        and settings.bucket_secret_access_key
        and settings.bucket_name
    )


@lru_cache
def _client():
    """The boto3 S3 client, built once per process from the bucket
    settings. signature_version="s3v4" is required by most S3-compatible
    providers (the older/anonymous default won't authenticate)."""
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.bucket_endpoint,
        aws_access_key_id=settings.bucket_access_key_id,
        aws_secret_access_key=settings.bucket_secret_access_key,
        region_name=settings.bucket_region,
        config=Config(signature_version="s3v4"),
    )


def new_video_key(filename: str) -> str:
    """A random, collision-proof object key for a new video upload,
    preserving the original extension — app/content.py's
    _analyze_video_url still needs to recognize it as a playable direct
    video file by extension once its presigned playback URL is built."""
    ext = Path(filename).suffix.lower()
    return f"videos/{uuid.uuid4().hex}{ext}"


def generate_upload_url(key: str, content_type: str) -> str:
    """A presigned PUT URL the admin's own browser uploads the video file
    to directly — see this module's docstring for why the app server
    itself never touches the bytes."""
    settings = get_settings()
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.bucket_name, "Key": key, "ContentType": content_type},
        ExpiresIn=UPLOAD_URL_EXPIRY_SECONDS,
    )


def generate_playback_url(key: str) -> str:
    """A presigned GET URL for playing back an uploaded video — generated
    fresh on every call rather than stored anywhere."""
    settings = get_settings()
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.bucket_name, "Key": key},
        ExpiresIn=PLAYBACK_URL_EXPIRY_SECONDS,
    )


def delete_video(key: str) -> None:
    """Removes an uploaded video from the bucket — called when a
    GalleryItem referencing one is deleted or replaced, so bucket storage
    (unlike the local volume's fixed allocation) doesn't quietly grow
    forever. Never raises — a failed cleanup shouldn't block the
    GalleryItem delete/update that triggered it."""
    if not bucket_configured():
        return
    settings = get_settings()
    try:
        _client().delete_object(Bucket=settings.bucket_name, Key=key)
    except Exception as exc:
        print(f"[storage] Failed to delete {key!r}: {exc}", flush=True)
