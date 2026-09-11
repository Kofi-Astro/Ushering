"""Entry point for the PUBLIC website (the marketing site + booking API).

Run with:  uvicorn app.main:app --reload --port 8000

This file is responsible for:
  1. Creating the database tables and seeding starter content on first run.
  2. Building the public FastAPI `app` — static file mounts, the page
     routes, and the booking-form API.
  3. Grafting the separate admin panel (`app.admin.admin_app`) onto this
     same process, but served on its own hostname (see the Host() mount
     near the bottom) rather than as a path under this app.

There is no build step. Templates are rendered fresh on every request
straight from the database — see app/content.py.
"""

import asyncio
import contextlib
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Host

from . import analytics, backup, error_alerts
from .admin import admin_app
from .config import get_settings
from .database import Base, SessionLocal, engine
from .routers import bookings, manage_booking, pages
from .seed import seed_if_empty

settings = get_settings()

# Absolute path to the repo root (this file lives at app/main.py, so two
# parents up). Used below to build absolute paths for the static mounts,
# which keeps things working regardless of the working directory uvicorn
# is started from.
ROOT_DIR = Path(__file__).resolve().parent.parent

# Create any tables that don't exist yet (SQLAlchemy's create_all is a
# no-op for tables that already exist, so this is safe to run on every
# startup — it does NOT run migrations for schema changes on existing
# tables, only creates missing ones from scratch).
Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    # Only inserts rows if the corresponding table is completely empty, so
    # this never overwrites anything the business owner has since edited
    # through the admin panel. See app/seed.py for exactly what it adds.
    seed_if_empty(db)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs app/backup.py's run_backup() once at startup and then every
    24 hours for as long as the process lives — see app/backup.py for why
    this is a plain JSON-export-to-bucket rather than a native Postgres
    dump (no pg_dump binary in the Railway container). Backups are a
    blocking operation (DB reads + gzip + an S3 upload), so it runs in a
    worker thread via asyncio.to_thread rather than on the event loop
    itself, keeping the site responsive to real requests while a backup
    is in progress."""

    async def backup_loop():
        while True:
            await asyncio.to_thread(backup.run_backup)
            await asyncio.sleep(backup.SCHEDULE_INTERVAL_SECONDS)

    task = asyncio.create_task(backup_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="GPS Ushering and Events", lifespan=lifespan)

# Allows the booking form's fetch() call to work even if the public site
# and this backend ever end up served from different origins. Not needed
# for the default same-origin setup (same app, same domain), but harmless
# to leave configured in case that ever changes. See app/config.py's
# FRONTEND_ORIGINS env var.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Site assets referenced as /css/... and /js/... throughout the templates.
app.mount("/css", StaticFiles(directory=str(ROOT_DIR / "app" / "static" / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(ROOT_DIR / "app" / "static" / "js")), name="js")
# Photos/videos uploaded through the admin's Gallery section land here.
app.mount("/images", StaticFiles(directory=str(ROOT_DIR / "images")), name="images")

# The site's actual pages (/, /about.html, /services.html, ...) plus
# /sitemap.xml and /robots.txt — see app/routers/pages.py.
app.include_router(pages.router)
# The public Book Us form posts here: POST /api/bookings. Public and
# unauthenticated on purpose (it's how a visitor submits an inquiry) — see
# app/routers/bookings.py for the spam-honeypot handling.
app.include_router(bookings.router)
# A customer's own self-service page for their booking (GET/POST
# /manage-booking/{token}) — also public, "authenticated" only by knowing
# the unguessable token in their own link. See app/routers/manage_booking.py.
app.include_router(manage_booking.router)

# The admin panel (bookings + all content management) is a SEPARATE
# FastAPI app — see app/admin/__init__.py — served on its own hostname:
# admin.localhost locally (resolves to 127.0.0.1 in any modern browser
# with zero /etc/hosts editing), e.g. admin.gpsusheringandevents.com in
# production (see ADMIN_HOSTNAME in app/config.py / .env.example).
#
# Host() is a Starlette route matcher that inspects the incoming request's
# Host header; if it matches settings.admin_hostname, the ENTIRE request
# is handed off to admin_app instead of being handled by any route below.
# Because admin_app has its own clean top-level routes (/, /login,
# /bookings, /services, ...), no path-prefix rewriting is needed anywhere
# — every admin-side link and redirect just works, regardless of which
# hostname it's reached through.
#
# It's inserted at index 0 so it's checked before the public routes above
# — otherwise a request to admin.<domain>/ could incorrectly match this
# app's own "/" route instead of being handed to admin_app.
app.router.routes.insert(0, Host(settings.admin_hostname, app=admin_app))


def _log_page_view(path: str, referrer: str | None, user_agent: str) -> None:
    with SessionLocal() as db:
        analytics.log_view(db, path, referrer, user_agent)


@app.middleware("http")
async def page_view_logger(request: Request, call_next):
    """Logs a PageView row (see app/models.py, app/analytics.py) for real,
    successful page visits — see analytics.should_log for exactly what's
    excluded (static assets, the booking API, bots). The DB write happens
    via the response's background task, after the response is already on
    its way to the visitor, so this never adds latency to the page they're
    waiting on."""
    response = await call_next(request)
    user_agent = request.headers.get("user-agent", "")
    if analytics.should_log(request.url.path, request.method, response.status_code, user_agent):
        response.background = BackgroundTask(
            _log_page_view, request.url.path, request.headers.get("referer"), user_agent
        )
    return response


@app.exception_handler(Exception)
async def unhandled_error_alert(request: Request, exc: Exception):
    """Emails a developer (see app/error_alerts.py) the moment a genuine
    unhandled bug reaches the public site. Only ever reached for actual
    bugs — HTTPException-based responses (the 404 handler below, /api
    validation errors, etc.) are handled separately by Starlette before
    this is ever consulted. The alert is sent via the response's
    background task rather than awaited here, so a slow SMTP server never
    delays the error response a visitor is already looking at."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
        background=BackgroundTask(error_alerts.maybe_send_alert, request, exc),
    )


@app.get("/health")
def health():
    """Trivial liveness check — Railway (or any host) can hit this to
    confirm the process is up and responding."""
    return {"status": "ok"}


@app.exception_handler(StarletteHTTPException)
async def not_found_page(request: Request, exc: StarletteHTTPException):
    """A bad/stale URL used to show FastAPI's bare default
    `{"detail":"Not Found"}` JSON — jarring for a visitor who mistyped a
    link or followed an outdated one. Every OTHER HTTP exception (a 422
    from /api/bookings' validation, etc.) is untouched, falling straight
    through to FastAPI's normal handling — this only replaces the 404
    case, and only branded (styled, on-site navigation) rather than
    changed in meaning. Registered on this app specifically, not
    admin_app (see app/admin/__init__.py) — the admin panel is for the
    one business owner, a plain 404 there is a non-issue."""
    if exc.status_code == 404:
        return pages.templates.TemplateResponse(
            request,
            "pages/404.html",
            pages.base_context(
                request,
                nav=None,
                title="Page Not Found | GPS Ushering and Events",
                description="The page you're looking for doesn't exist.",
                robots="noindex, nofollow",
            ),
            status_code=404,
        )
    return await http_exception_handler(request, exc)
