"""A single value that changes on every real deploy, appended as a
?v=... query string to every CSS/JS asset link in base.html and
admin/base.html. Railway's own edge (the `x-cache: HIT` / `server:
railway-hikari` response headers on /css/style.css, /js/main.js, etc.)
has been observed serving a stale cached copy of these files for several
minutes after a deploy — confirmed directly: a fresh curl got the new
CSS immediately, while a browser request through a different edge node
got a copy over 8 minutes stale. A cache HIT keyed on the plain,
un-versioned URL is a cache MISS the instant the URL's query string
changes, so this forces every deploy to be served fresh regardless of
whatever TTL Railway's edge applies underneath — no visibility into (or
control over) that TTL is needed.

Prefers Railway's own RAILWAY_GIT_COMMIT_SHA (set automatically on
Railway deployments), so the version stays stable across every request
and worker process for the same actual deploy. Falls back to this
process's own start time when that env var isn't set (e.g. local dev) —
still correct, just busts the cache on every restart too, not only a
genuine code change, which is harmless.
"""

import os
import time

ASSET_VERSION = os.environ.get("RAILWAY_GIT_COMMIT_SHA", str(int(time.time())))[:12]
