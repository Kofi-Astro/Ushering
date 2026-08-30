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

from .routers import auth, bookings, faq, gallery, home, services, settings, testimonials

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

admin_app = FastAPI(title="GPS Ushering and Events — Admin")

admin_app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "app" / "static")), name="static")
admin_app.mount("/images", StaticFiles(directory=str(ROOT_DIR / "images")), name="images")

admin_app.include_router(auth.router)
admin_app.include_router(home.router)
admin_app.include_router(bookings.router)
admin_app.include_router(services.router)
admin_app.include_router(gallery.router)
admin_app.include_router(testimonials.router)
admin_app.include_router(faq.router)
admin_app.include_router(settings.router)
