"""The unified admin panel — bookings + all content management (services,
gallery, testimonials, FAQ, site settings) behind one login. Built as its
own FastAPI app so it can be served on its own hostname (see app/main.py,
which mounts this via Starlette's Host() matcher against settings.admin_hostname)
without any path-prefix rewriting: every route here is a clean top-level
path (/, /login, /bookings, /services, ...) that resolves correctly
whichever hostname it's reached through.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import auth, bookings, faq, gallery, home, services, settings, site_text, testimonials

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

admin_app = FastAPI(title="GPS Ushering and Events — Admin")

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
admin_app.include_router(testimonials.router)  # /testimonials
admin_app.include_router(faq.router)           # /faq
admin_app.include_router(settings.router)      # /settings
admin_app.include_router(site_text.router)     # /page-text
