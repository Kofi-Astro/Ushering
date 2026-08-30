from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, engine
from .routers import admin, bookings, oauth

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="GPS Ushering and Events — Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount(
    "/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static"
)

app.include_router(bookings.router)
app.include_router(admin.router)
app.include_router(oauth.router)


@app.get("/health")
def health():
    return {"status": "ok"}
