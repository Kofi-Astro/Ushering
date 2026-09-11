"""The admin panel's Analytics section — a read-only dashboard over the
page views app/main.py's middleware logs via app/analytics.py. No
CRUD here, just app/analytics.py:get_summary rendered into a page.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ... import analytics
from ...asset_version import ASSET_VERSION
from ...database import get_db
from ...security import require_admin

router = APIRouter(prefix="/analytics", tags=["analytics-admin"], dependencies=[Depends(require_admin)])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))
templates.env.globals["asset_version"] = ASSET_VERSION


@router.get("")
def analytics_dashboard(request: Request, db: Session = Depends(get_db)):
    summary = analytics.get_summary(db)
    return templates.TemplateResponse(
        request,
        "admin/analytics.html",
        {"title": "Analytics", "active": "analytics", **summary},
    )
