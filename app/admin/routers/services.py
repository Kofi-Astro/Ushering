"""The admin panel's Services section — full CRUD (list, create, edit,
delete) for the Service table.

This is the "template" CRUD router — testimonials.py, gallery.py and
faq.py all follow this exact same 5-route shape (list / new form / create
/ edit form+update / delete), just with different fields. If you're
reading one of those and something's unclear, this file has the fullest
comments.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Service
from ...security import require_admin

router = APIRouter(prefix="/services", tags=["services-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("")
def list_services(request: Request, db: Session = Depends(get_db)):
    """The /services landing page: every service, in display order, each
    with Edit/Delete buttons and an "Add Service" link to /services/new."""
    services = db.query(Service).order_by(Service.order).all()
    return templates.TemplateResponse(
        request, "admin/services_list.html", {"title": "Services", "active": "services", "services": services}
    )


@router.get("/new")
def new_service_form(request: Request):
    """Blank version of the same form template used for editing —
    `service=None` in the context tells admin/service_form.html to show
    empty fields and POST to /services/new instead of an edit URL."""
    return templates.TemplateResponse(
        request, "admin/service_form.html", {"title": "Add Service", "active": "services", "service": None}
    )


@router.post("/new")
def create_service(
    title: str = Form(...),
    icon: str = Form(...),
    order: int = Form(1),
    home_description: str = Form(...),
    description: str = Form(...),
    highlights: str = Form(""),
    db: Session = Depends(get_db),
):
    """Handles the "Add Service" form submit. FastAPI parses each Form(...)
    parameter straight out of the multipart/urlencoded form body — no
    manual request.form() parsing needed."""
    service = Service(
        title=title,
        icon=icon,
        order=order,
        home_description=home_description,
        description=description,
        highlights=highlights,
    )
    db.add(service)
    db.commit()
    return RedirectResponse(url="/services", status_code=303)


@router.get("/{service_id}/edit")
def edit_service_form(service_id: int, request: Request, db: Session = Depends(get_db)):
    """Same template as new_service_form, but pre-filled: `service` here
    is the actual row, not None, so the form fields show its current
    values and POST to /services/{id}/edit instead of /services/new."""
    service = db.query(Service).filter(Service.id == service_id).first()
    return templates.TemplateResponse(
        request, "admin/service_form.html", {"title": "Edit Service", "active": "services", "service": service}
    )


@router.post("/{service_id}/edit")
def update_service(
    service_id: int,
    title: str = Form(...),
    icon: str = Form(...),
    order: int = Form(1),
    home_description: str = Form(...),
    description: str = Form(...),
    highlights: str = Form(""),
    db: Session = Depends(get_db),
):
    """Handles the edit form's submit. Silently does nothing if the id
    doesn't exist (shouldn't happen in normal use through the UI)."""
    service = db.query(Service).filter(Service.id == service_id).first()
    if service:
        service.title = title
        service.icon = icon
        service.order = order
        service.home_description = home_description
        service.description = description
        service.highlights = highlights
        db.commit()
    return RedirectResponse(url="/services", status_code=303)


@router.post("/{service_id}/delete")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    """Handles the Delete button on the services list (which confirms via
    a JS `confirm()` dialog before submitting — see admin/services_list.html)."""
    service = db.query(Service).filter(Service.id == service_id).first()
    if service:
        db.delete(service)
        db.commit()
    return RedirectResponse(url="/services", status_code=303)
