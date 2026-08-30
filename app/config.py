from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "change-me"
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
    frontend_origins: str = "*"
    database_url: str = "sqlite:///./bookings.db"

    @property
    def allowed_origins(self) -> list[str]:
        if self.frontend_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
