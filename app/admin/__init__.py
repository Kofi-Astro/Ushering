"""The unified admin panel — bookings + all content management (services,
gallery, testimonials, FAQ, site settings) behind one login. Built as its
own FastAPI app so it can be served on its own hostname (see app/main.py,
which mounts this via Starlette's Host() matcher against settings.admin_hostname)
without any path-prefix rewriting: every route here is a clean top-level
path (/, /login, /bookings, /services, ...) that resolves correctly
whichever hostname it's reached through.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from .. import error_alerts
from .routers import analytics, auth, bookings, faq, gallery, home, services, settings, site_text, team_photos, testimonials

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

admin_app = FastAPI(title="GPS Ushering and Events — Admin")


@admin_app.exception_handler(Exception)
async def unhandled_error_alert(request: Request, exc: Exception):
    """Emails a developer (see app/error_alerts.py) the moment a genuine
    unhandled bug reaches the admin panel — FastAPI's own HTTPException
    handling (404s, the require_admin redirect, etc.) is untouched, since
    this only catches plain Exception, which HTTPException isn't. The
    alert itself is sent via the response's background task (see
    starlette.background.BackgroundTask) rather than awaited here, so a
    slow SMTP server never delays the error response the admin is
    already waiting on."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
        background=BackgroundTask(error_alerts.maybe_send_alert, request, exc),
    )

# Admin templates reference /static/admin.css, and the Gallery section's
# edit form previews uploaded photos via /images/uploads/... — since this
# is a separate FastAPI app from the public one, it needs its own mounts
# for both, even though they point at the exact same directories on disk.
admin_app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "app" / "static")), name="static")
admin_app.mount("/images", StaticFiles(directory=str(ROOT_DIR / "images")), name="images")

# auth: /login, /logout — must come first conceptually (everything else
# depends on being logged in), though route registration order doesn't
# actually matter here since none of these paths overlap.
admin_app.include_router(auth.router)
admin_app.include_router(home.router)          # / — dashboard landing
admin_app.include_router(bookings.router)      # /bookings
admin_app.include_router(services.router)      # /services
admin_app.include_router(gallery.router)       # /gallery
admin_app.include_router(team_photos.router)   # /team-photos
admin_app.include_router(testimonials.router)  # /testimonials
admin_app.include_router(faq.router)           # /faq
admin_app.include_router(settings.router)      # /settings
admin_app.include_router(site_text.router)     # /page-text
admin_app.include_router(analytics.router)     # /analytics
