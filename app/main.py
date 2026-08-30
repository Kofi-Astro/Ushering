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

ROOT_DIR = Path(__file__).resolve().parent.parent

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_if_empty(db)

app = FastAPI(title="GPS Ushering and Events")

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

app.include_router(pages.router)
app.include_router(bookings.router)

# The admin panel (bookings + content management) is a separate FastAPI app,
# served on its own hostname — admin.localhost locally, e.g.
# admin.gpsusheringandevents.com in production (see ADMIN_HOSTNAME).
# Host() matches on the request's Host header and dispatches the whole
# request to admin_app, which has its own top-level routes (/, /login,
# /bookings, /services, ...) unrelated to any path on the main site.
app.router.routes.insert(0, Host(settings.admin_hostname, app=admin_app))


@app.get("/health")
def health():
    return {"status": "ok"}
