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
    services = db.query(Service).order_by(Service.order).all()
    return templates.TemplateResponse(
        request, "admin/services_list.html", {"title": "Services", "active": "services", "services": services}
    )


@router.get("/new")
def new_service_form(request: Request):
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
    service = db.query(Service).filter(Service.id == service_id).first()
    if service:
        db.delete(service)
        db.commit()
    return RedirectResponse(url="/services", status_code=303)
