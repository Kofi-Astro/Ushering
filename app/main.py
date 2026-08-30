from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, engine
from .routers import admin, bookings, oauth, pages

settings = get_settings()

ROOT_DIR = Path(__file__).resolve().parent.parent

Base.metadata.create_all(bind=engine)

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
# Admin-dashboard-only assets (e.g. admin.css) and anything else dropped in app/static.
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "app" / "static")), name="static")
# Photos/videos uploaded through the content-admin (Decap CMS) land here.
app.mount("/images", StaticFiles(directory=str(ROOT_DIR / "images")), name="images")
# The content-admin itself: a static Decap CMS shell (index.html + config.yml).
app.mount(
    "/content-admin",
    StaticFiles(directory=str(ROOT_DIR / "content-admin"), html=True),
    name="content-admin",
)

app.include_router(pages.router)
app.include_router(bookings.router)
app.include_router(admin.router)
app.include_router(oauth.router)


@app.get("/health")
def health():
    return {"status": "ok"}
