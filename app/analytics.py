"""Lightweight, privacy-respecting page-view tracking. See
app/models.py:PageView for exactly what is (and deliberately isn't)
recorded, app/main.py for the middleware that calls log_view on every
request, and app/admin/routers/analytics.py for the dashboard that reads
it back.
"""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import PageView

# Anything with one of these substrings in its User-Agent is a bot,
# crawler, or another server's own health/monitoring check — not a real
# visitor, so it's excluded before ever reaching the database. Not
# exhaustive (no list ever is), just the common, high-volume ones.
_BOT_MARKERS = (
    "bot", "spider", "crawl", "curl/", "python-requests", "wget",
    "facebookexternalhit", "monitoring", "pingdom", "uptimerobot",
)
# Static assets, the JSON API, and infra endpoints aren't "pages" a
# visitor reads — logging them would just be noise in the dashboard.
_SKIP_PREFIXES = ("/css/", "/js/", "/images/", "/static/", "/api/", "/health")
_SKIP_PATHS = {"/sitemap.xml", "/robots.txt", "/favicon.ico"}


def should_log(path: str, method: str, status_code: int, user_agent: str) -> bool:
    """Whether a request is worth recording as a page view at all."""
    if method != "GET" or status_code >= 400:
        return False
    if path in _SKIP_PATHS or any(path.startswith(prefix) for prefix in _SKIP_PREFIXES):
        return False
    ua_lower = (user_agent or "").lower()
    return not any(marker in ua_lower for marker in _BOT_MARKERS)


def is_mobile_ua(user_agent: str) -> bool:
    """A quick, approximate mobile/desktop guess from the User-Agent
    string — the string itself is never stored, only this one bit."""
    ua_lower = (user_agent or "").lower()
    return any(marker in ua_lower for marker in ("mobi", "android", "iphone", "ipad"))


def log_view(db: Session, path: str, referrer: str | None, user_agent: str) -> None:
    db.add(PageView(path=path, referrer=(referrer or "")[:500] or None, is_mobile=is_mobile_ua(user_agent)))
    db.commit()


def get_summary(db: Session) -> dict:
    """Everything the admin Analytics page shows, computed fresh on every
    request — this dashboard is checked occasionally, not on a hot path,
    so there's no need for the caching every other read in this app
    already avoids on principle (see app/content.py's module docstring)."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    count_today = db.query(func.count(PageView.id)).filter(PageView.created_at >= today_start).scalar() or 0
    count_7d = db.query(func.count(PageView.id)).filter(PageView.created_at >= since_7d).scalar() or 0
    count_30d = db.query(func.count(PageView.id)).filter(PageView.created_at >= since_30d).scalar() or 0

    top_pages = (
        db.query(PageView.path, func.count(PageView.id).label("views"))
        .filter(PageView.created_at >= since_30d)
        .group_by(PageView.path)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )
    top_referrers = (
        db.query(PageView.referrer, func.count(PageView.id).label("views"))
        .filter(PageView.created_at >= since_30d, PageView.referrer.isnot(None))
        .group_by(PageView.referrer)
        .order_by(func.count(PageView.id).desc())
        .limit(10)
        .all()
    )
    mobile_30d = (
        db.query(func.count(PageView.id)).filter(PageView.created_at >= since_30d, PageView.is_mobile.is_(True)).scalar()
        or 0
    )

    # Daily counts for the last 14 days, oldest first, zero-filled for a
    # day with no views at all rather than skipping it in the list.
    daily_counts = []
    for days_ago in range(13, -1, -1):
        day_start = today_start - timedelta(days=days_ago)
        day_end = day_start + timedelta(days=1)
        count = (
            db.query(func.count(PageView.id))
            .filter(PageView.created_at >= day_start, PageView.created_at < day_end)
            .scalar()
            or 0
        )
        daily_counts.append({"date": day_start.strftime("%b %d"), "count": count})
    max_daily = max((d["count"] for d in daily_counts), default=0)

    return {
        "count_today": count_today,
        "count_7d": count_7d,
        "count_30d": count_30d,
        "mobile_30d": mobile_30d,
        "mobile_pct": round(mobile_30d / count_30d * 100) if count_30d else 0,
        "top_pages": [{"path": path, "views": views} for path, views in top_pages],
        "top_referrers": [{"referrer": ref, "views": views} for ref, views in top_referrers],
        "daily_counts": daily_counts,
        "max_daily": max_daily,
    }
