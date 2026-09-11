"""Sends a developer an email the moment an unhandled exception reaches
either FastAPI app — the public site (app/main.py) or the admin panel
(app/admin/__init__.py), both of which register maybe_send_alert below
as their catch-all exception handler.

Rate-limited per distinct error (same exception type + the file/line it
was raised from) via an in-memory cooldown, so one recurring bug sends
one alert per COOLDOWN_SECONDS rather than flooding the inbox with a
copy per request. This resets on every restart/redeploy — acceptable,
since a fresh alert right after a deploy (rather than staying silent
because the same bug alerted once, days ago, before the restart) is
arguably the more useful behavior, not less.
"""

import time
import traceback

from fastapi import Request

from .config import get_settings
from .email_notify import send_error_alert

COOLDOWN_SECONDS = 60 * 60  # 1 hour
_last_alerted: dict[str, float] = {}


def _error_signature(exc: Exception) -> str:
    """Identifies "the same error" as exception type + where it was
    raised, so two different bugs never suppress each other's alerts,
    but the exact same crash repeating (e.g. on every request to a
    broken route) only alerts once per cooldown."""
    frames = traceback.extract_tb(exc.__traceback__)
    location = f"{frames[-1].filename}:{frames[-1].lineno}" if frames else "unknown"
    return f"{type(exc).__name__}@{location}"


def maybe_send_alert(request: Request, exc: Exception) -> None:
    """Called from both apps' catch-all exception handlers. Does nothing
    if error_alert_email isn't configured, or if this exact error already
    alerted within the last COOLDOWN_SECONDS. Never raises — a problem
    sending the alert itself must not be able to break the error response
    the caller still needs to return."""
    try:
        recipient = get_settings().error_alert_email
        if not recipient:
            return
        signature = _error_signature(exc)
        now = time.time()
        if now - _last_alerted.get(signature, 0) < COOLDOWN_SECONDS:
            return
        _last_alerted[signature] = now
        trace_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        send_error_alert(
            summary=f"{type(exc).__name__}: {exc}",
            request_path=str(request.url),
            traceback_text=trace_text,
            recipient_email=recipient,
        )
    except Exception as alert_exc:
        print(f"[error_alerts] Failed to send alert: {alert_exc}", flush=True)
