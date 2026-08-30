"""Central app configuration, read from environment variables (or a local
.env file — see .env.example for every variable this recognizes).

pydantic-settings does the parsing: each attribute below becomes an env
var of the same name in SCREAMING_CASE (e.g. `secret_key` <- SECRET_KEY).
Everywhere else in the codebase, get_settings() is the only way settings
are read — never read os.environ directly, so all config stays in one
place with one set of defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Signs the admin session cookie (see app/security.py). Change this in
    # production — anyone who knows it could forge a valid login cookie.
    secret_key: str = "change-me"
    # The one admin account for the whole admin panel — see
    # app/security.py:check_credentials. There's no user table; this is a
    # single hardcoded login, which is fine since there's exactly one
    # person (the business owner) who needs access.
    admin_username: str = "admin"
    admin_password: str = "change-me"
    # Browsers reject a `Secure` cookie over plain http:// (curl doesn't care,
    # which is why this can look fine in local testing but silently fail to
    # persist a login in a real browser). Leave true for Railway (HTTPS);
    # set to false only for local dev over http://localhost.
    cookie_secure: bool = True
    # The admin panel (bookings + content management) is served as a
    # separate virtual host, matched against the incoming request's Host
    # header (see app/main.py). Defaults to admin.localhost, which modern
    # browsers and OSes resolve to 127.0.0.1 with no /etc/hosts editing
    # needed — visit it directly during local development. Set this to
    # your real admin subdomain (e.g. admin.gpsusheringandevents.com) in
    # production.
    admin_hostname: str = "admin.localhost"
    # Comma-separated list of origins allowed to POST to /api/bookings via
    # fetch(). "*" (the default) is fine for the normal same-origin setup
    # (public site and this backend on the same domain) — only matters if
    # the frontend is ever split onto a different domain than this API.
    frontend_origins: str = "*"
    # SQLite by default (zero setup for local dev). On Railway, adding a
    # Postgres plugin makes Railway inject a real DATABASE_URL — see
    # app/database.py for how that URL gets adapted to use psycopg (v3).
    database_url: str = "sqlite:///./bookings.db"

    @property
    def allowed_origins(self) -> list[str]:
        """Turns the raw FRONTEND_ORIGINS env var into the list shape
        FastAPI's CORSMiddleware expects."""
        if self.frontend_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Returns the single shared Settings instance, reading env vars only
    once per process (lru_cache with no arguments memoizes on first call)."""
    return Settings()
