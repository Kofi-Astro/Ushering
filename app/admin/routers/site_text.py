"""The admin panel's "Page Text" section — lets the business owner edit
every heading, paragraph, button label and similar piece of copy on the
public site that isn't already covered by the Services / Testimonials /
Gallery / FAQ / Settings sections. Unlike those, there's no single
SiteText row worth showing on its own — there are 140+ of them — so
instead of one route per row, this groups them by page (see
app/site_text_catalog.py's GROUPS) and edits a whole page's worth of text
in one form submit.

Fields are collected dynamically from the submitted form data rather than
declared as ~140 individual FastAPI Form(...) parameters — each group's
own field list (from the catalog) says which keys to expect and save.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from ...database import get_db
from ...models import SiteText
from ...security import require_admin
from ...site_text_catalog import GROUPS

router = APIRouter(prefix="/page-text", tags=["site-text-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("")
def page_text_index(request: Request):
    """Landing page: just a list of groups linking to each one's edit
    form — there's no single "Page Text" row to show, so this is here
    mainly so /page-text is a sensible link target from the admin nav."""
    return templates.TemplateResponse(
        request,
        "admin/site_text_index.html",
        {"title": "Page Text", "active": "page_text", "groups": GROUPS},
    )


@router.get("/{group_key}")
def edit_group(group_key: str, request: Request, saved: bool = False, db: Session = Depends(get_db)):
    """Pre-filled form for one group's worth of fields, e.g. every piece
    of copy on the homepage."""
    group = GROUPS.get(group_key)
    if group is None:
        raise HTTPException(status_code=404)
    saved_values = {row.key: row.value for row in db.query(SiteText).filter(SiteText.key.in_([f.key for f in group.fields])).all()}
    fields = [(f, saved_values.get(f.key, f.default)) for f in group.fields]
    return templates.TemplateResponse(
        request,
        "admin/site_text_form.html",
        {
            "title": group.title,
            "active": "page_text",
            "groups": GROUPS,
            "group_key": group_key,
            "group": group,
            "fields": fields,
            "message": "Saved." if saved else None,
        },
    )


@router.post("/{group_key}")
async def update_group(group_key: str, request: Request, db: Session = Depends(get_db)):
    """Handles a group's form submit. Only the keys declared in this
    group's own field list are touched, so posting the homepage form can
    never accidentally affect another page's text even if the form data
    contained extra/unexpected keys."""
    group = GROUPS.get(group_key)
    if group is None:
        raise HTTPException(status_code=404)
    form = await request.form()
    keys = [f.key for f in group.fields]
    existing = {row.key: row for row in db.query(SiteText).filter(SiteText.key.in_(keys)).all()}
    for f in group.fields:
        value = str(form.get(f.key, "")).strip()
        if f.key in existing:
            existing[f.key].value = value
        else:
            db.add(SiteText(key=f.key, value=value))
    db.commit()
    return RedirectResponse(url=f"/page-text/{group_key}?saved=1", status_code=303)
