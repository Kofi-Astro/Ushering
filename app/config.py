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
    frontend_origins: str = "*"
    database_url: str = "sqlite:///./bookings.db"

    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""

    @property
    def allowed_origins(self) -> list[str]:
        if self.frontend_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
