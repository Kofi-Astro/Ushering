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

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.routing import Host

from .admin import admin_app
from .config import get_settings
from .database import Base, SessionLocal, engine
from .routers import bookings, pages
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

app = FastAPI(title="GPS Ushering and Events")

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


@app.get("/health")
def health():
    """Trivial liveness check — Railway (or any host) can hit this to
    confirm the process is up and responding."""
    return {"status": "ok"}
