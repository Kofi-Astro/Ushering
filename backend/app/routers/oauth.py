"""GitHub OAuth proxy for the Decap CMS content admin at /admin on the
marketing site (a separate static site — not this service's own /admin
booking dashboard). Decap's "github" backend needs a small server that can
hold the OAuth app's client secret; this fills that role so the CMS can run
without depending on Netlify Identity.

Setup: register a GitHub OAuth App at https://github.com/settings/developers
with "Authorization callback URL" = <this service's public URL>/callback,
then set GITHUB_OAUTH_CLIENT_ID / GITHUB_OAUTH_CLIENT_SECRET in the
environment. Point admin/config.yml's backend.base_url at this service.
"""

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from ..config import get_settings

router = APIRouter(tags=["oauth"])
settings = get_settings()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


@router.get("/auth")
def auth(scope: str = "repo,user"):
    if not settings.github_oauth_client_id:
        raise HTTPException(500, "GITHUB_OAUTH_CLIENT_ID is not configured")
    params = f"client_id={settings.github_oauth_client_id}&scope={scope}"
    return RedirectResponse(url=f"{GITHUB_AUTHORIZE_URL}?{params}")


@router.get("/callback", response_class=HTMLResponse)
def callback(code: str | None = None):
    if not code:
        raise HTTPException(400, "Missing OAuth code from GitHub")

    response = httpx.post(
        GITHUB_TOKEN_URL,
        data={
            "client_id": settings.github_oauth_client_id,
            "client_secret": settings.github_oauth_client_secret,
            "code": code,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    response.raise_for_status()
    token_data = response.json()
    token = token_data.get("access_token")
    if not token:
        raise HTTPException(400, f"GitHub did not return a token: {token_data}")

    # Decap CMS handshake: the popup waits for the opener to signal it's
    # listening, then posts the token back. Doing it in this order (rather
    # than posting immediately) avoids a race where the message fires before
    # the CMS has attached its listener.
    message = f'authorization:github:success:{{"token":"{token}","provider":"github"}}'
    html = f"""<!doctype html>
<html><body>
<script>
(function () {{
  function receiveMessage(e) {{
    window.opener.postMessage(
      '{message}',
      e.origin
    );
    window.removeEventListener("message", receiveMessage, false);
  }}
  window.addEventListener("message", receiveMessage, false);
  window.opener.postMessage("authorizing:github", "*");
}})();
</script>
</body></html>"""
    return HTMLResponse(content=html)
