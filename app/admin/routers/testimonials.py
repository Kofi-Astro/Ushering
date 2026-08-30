from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Testimonial
from ...security import require_admin

router = APIRouter(prefix="/testimonials", tags=["testimonials-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("")
def list_testimonials(request: Request, db: Session = Depends(get_db)):
    testimonials = db.query(Testimonial).order_by(Testimonial.order).all()
    return templates.TemplateResponse(
        request,
        "admin/testimonials_list.html",
        {"title": "Testimonials", "active": "testimonials", "testimonials": testimonials},
    )


@router.get("/new")
def new_testimonial_form(request: Request):
    return templates.TemplateResponse(
        request, "admin/testimonial_form.html", {"title": "Add Testimonial", "active": "testimonials", "testimonial": None}
    )


@router.post("/new")
def create_testimonial(
    name: str = Form(...),
    role: str = Form(...),
    rating: int = Form(5),
    order: int = Form(1),
    quote: str = Form(...),
    db: Session = Depends(get_db),
):
    db.add(Testimonial(name=name, role=role, rating=rating, order=order, quote=quote))
    db.commit()
    return RedirectResponse(url="/testimonials", status_code=303)


@router.get("/{testimonial_id}/edit")
def edit_testimonial_form(testimonial_id: int, request: Request, db: Session = Depends(get_db)):
    testimonial = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    return templates.TemplateResponse(
        request,
        "admin/testimonial_form.html",
        {"title": "Edit Testimonial", "active": "testimonials", "testimonial": testimonial},
    )


@router.post("/{testimonial_id}/edit")
def update_testimonial(
    testimonial_id: int,
    name: str = Form(...),
    role: str = Form(...),
    rating: int = Form(5),
    order: int = Form(1),
    quote: str = Form(...),
    db: Session = Depends(get_db),
):
    testimonial = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if testimonial:
        testimonial.name = name
        testimonial.role = role
        testimonial.rating = rating
        testimonial.order = order
        testimonial.quote = quote
        db.commit()
    return RedirectResponse(url="/testimonials", status_code=303)


@router.post("/{testimonial_id}/delete")
def delete_testimonial(testimonial_id: int, db: Session = Depends(get_db)):
    testimonial = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if testimonial:
        db.delete(testimonial)
        db.commit()
    return RedirectResponse(url="/testimonials", status_code=303)
