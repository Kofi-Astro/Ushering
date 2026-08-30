from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import FAQItem
from ...security import require_admin

router = APIRouter(prefix="/faq", tags=["faq-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("")
def list_faq(request: Request, db: Session = Depends(get_db)):
    faqs = db.query(FAQItem).order_by(FAQItem.order).all()
    return templates.TemplateResponse(request, "admin/faq_list.html", {"title": "FAQ", "active": "faq", "faqs": faqs})


@router.get("/new")
def new_faq_form(request: Request):
    return templates.TemplateResponse(
        request, "admin/faq_form.html", {"title": "Add FAQ", "active": "faq", "faq": None}
    )


@router.post("/new")
def create_faq(
    question: str = Form(...),
    order: int = Form(1),
    answer: str = Form(...),
    db: Session = Depends(get_db),
):
    db.add(FAQItem(question=question, order=order, answer=answer))
    db.commit()
    return RedirectResponse(url="/faq", status_code=303)


@router.get("/{faq_id}/edit")
def edit_faq_form(faq_id: int, request: Request, db: Session = Depends(get_db)):
    faq = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    return templates.TemplateResponse(
        request, "admin/faq_form.html", {"title": "Edit FAQ", "active": "faq", "faq": faq}
    )


@router.post("/{faq_id}/edit")
def update_faq(
    faq_id: int,
    question: str = Form(...),
    order: int = Form(1),
    answer: str = Form(...),
    db: Session = Depends(get_db),
):
    faq = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    if faq:
        faq.question = question
        faq.order = order
        faq.answer = answer
        db.commit()
    return RedirectResponse(url="/faq", status_code=303)


@router.post("/{faq_id}/delete")
def delete_faq(faq_id: int, db: Session = Depends(get_db)):
    faq = db.query(FAQItem).filter(FAQItem.id == faq_id).first()
    if faq:
        db.delete(faq)
        db.commit()
    return RedirectResponse(url="/faq", status_code=303)
