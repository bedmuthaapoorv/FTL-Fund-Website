from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration comes from the environment (.env locally).
    Secrets never live in the repo; see .env.example."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "sqlite:///./dev.db"

    # Public origin of the site, used in invite links. No trailing slash.
    site_url: str = "http://localhost:5180"

    # Contact form delivery. "console" prints instead of sending (dev/test).
    email_backend: Literal["console", "smtp"] = "console"
    contact_to: str = "bedmuthaapoorv@gmail.com"
    mail_from: str = "bedmuthaapoorv@gmail.com"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Rate limits (slowapi syntax). Overridable so tests can tighten them.
    contact_rate_limit: str = "5/hour"
    login_rate_limit: str = "10/15minutes"

    # Shared secret for the FrontierTradeLight sync push (HMAC-SHA256).
    sync_secret: str = ""

    # Fernet key encrypting TOTP secrets at rest. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    data_encryption_key: str = ""

    # Session lifetimes.
    session_idle_minutes: int = 30
    session_absolute_hours: int = 8
    mfa_step_minutes: int = 5
    invite_valid_hours: int = 72

    # Account lockout after repeated failures (password or MFA).
    lockout_threshold: int = 5
    lockout_minutes: int = 15

    @property
    def secure_cookies(self) -> bool:
        return self.env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
