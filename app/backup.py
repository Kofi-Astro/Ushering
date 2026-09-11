"""Automatic database backups — every table in app/models.py, dumped to
JSON, gzipped, and uploaded to the Railway Bucket (see app/storage.py)
under backups/<timestamp>.json.gz. Runs once at startup and then every
24 hours (see app/main.py's lifespan), keeping the most recent
RETENTION_COUNT backups and pruning anything older.

Iterates SQLAlchemy's own mapper registry rather than a hardcoded list
of models, so a table added to models.py later is included automatically
with no change needed here.

Restoring is deliberately NOT exposed through any web route — it's a
disaster-recovery action for a developer to run manually (via `railway
ssh`, the same way the one-off poster-healing script was run), not
something safe to expose over HTTP. See restore_from_backup below.
"""

import gzip
import json
from datetime import date, datetime

from sqlalchemy import DateTime

from . import storage
from .database import Base, SessionLocal

BACKUP_PREFIX = "backups/"
RETENTION_COUNT = 14  # roughly two weeks of daily backups
SCHEDULE_INTERVAL_SECONDS = 24 * 60 * 60


def _serialize_value(value):
    """Makes a column value JSON-safe. Booking.status (a `str, Enum`
    subclass — see app/models.py:BookingStatus) already serializes fine
    as a plain string via json.dumps, so only datetime/date actually need
    conversion here."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _deserialize_value(column, value):
    """The inverse of _serialize_value, using the column's own declared
    type (via SQLAlchemy's mapper introspection) to know what to convert
    back — datetimes need to become real datetime objects again before
    being assigned to a DateTime column; an Enum column accepts its
    member's plain string value directly, so that one needs no change."""
    if value is None:
        return None
    if isinstance(column.type, DateTime):
        return datetime.fromisoformat(value)
    return value


def dump_all_tables() -> dict:
    """Every row of every mapped table, keyed by table name, as plain
    JSON-safe dicts keyed by column name — not tied to any particular
    model's Python shape, so this (and restore_from_backup) stay correct
    automatically as models.py changes."""
    data: dict[str, list[dict]] = {}
    with SessionLocal() as db:
        for mapper in Base.registry.mappers:
            model = mapper.class_
            columns = list(mapper.columns)
            rows = db.query(model).all()
            data[model.__tablename__] = [
                {col.key: _serialize_value(getattr(row, col.key)) for col in columns} for row in rows
            ]
    return data


def run_backup() -> str | None:
    """Dumps every table, uploads the gzipped JSON to the bucket, and
    prunes anything beyond the last RETENTION_COUNT backups. Returns the
    new backup's key on success; returns None (and never raises) if the
    bucket isn't configured or anything goes wrong — a failed backup
    attempt must never be able to crash whatever's running this (see
    app/main.py's lifespan-scheduled loop)."""
    if not storage.bucket_configured():
        return None
    try:
        payload = gzip.compress(json.dumps(dump_all_tables()).encode("utf-8"))
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        key = f"{BACKUP_PREFIX}{timestamp}.json.gz"
        storage.upload_bytes(key, payload, content_type="application/gzip")
        _prune_old_backups()
        return key
    except Exception as exc:
        print(f"[backup] Failed: {exc}", flush=True)
        return None


def _prune_old_backups() -> None:
    keys = storage.list_keys(BACKUP_PREFIX)
    if len(keys) <= RETENTION_COUNT:
        return
    for key in keys[: len(keys) - RETENTION_COUNT]:  # list_keys sorts oldest-first
        try:
            storage.delete_key(key)
        except Exception as exc:
            print(f"[backup] Failed to prune {key!r}: {exc}", flush=True)


def list_backups() -> list[str]:
    """Every backup's key, oldest to newest — shown on the admin
    dashboard (see app/admin/routers/home.py) so the business owner (or a
    developer checking in) can see at a glance that backups are actually
    happening, without needing bucket/CLI access to check."""
    if not storage.bucket_configured():
        return []
    return storage.list_keys(BACKUP_PREFIX)


def restore_from_backup(key: str) -> None:
    """Restores every table from a specific backup file: deletes all
    current rows in each table the backup has data for, then re-inserts
    the backed-up ones. Deliberately destructive and deliberately not
    reachable over HTTP — see this module's docstring. Nothing in this
    schema has a foreign key, so table order doesn't matter here.

    Usage (from a shell with this app importable, e.g. `railway ssh`):
        from app.backup import list_backups, restore_from_backup
        print(list_backups())  # pick a key
        restore_from_backup("backups/2026-09-11T00-00-00Z.json.gz")
    """
    data = json.loads(gzip.decompress(storage.download_bytes(key)))
    with SessionLocal() as db:
        for mapper in Base.registry.mappers:
            model = mapper.class_
            table_name = model.__tablename__
            if table_name not in data:
                continue
            db.query(model).delete()
            for row_dict in data[table_name]:
                coerced = {col.key: _deserialize_value(col, row_dict.get(col.key)) for col in mapper.columns}
                db.add(model(**coerced))
        db.commit()
