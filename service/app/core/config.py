import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("LICENSE_APP_NAME", "wp-api")
    owner_email: str = os.getenv("LICENSE_OWNER_EMAIL", "mago@dono.pd").strip().lower()
    owner_password: str = os.getenv("LICENSE_OWNER_PASSWORD", "12345678")
    owner_name: str = os.getenv("LICENSE_OWNER_NAME", "Mago Dono").strip()
    database_url: str = os.getenv(
        "LICENSE_DATABASE_URL",
        "postgresql+psycopg://license_user:change-me@127.0.0.1:5432/license_central",
    )
    api_admin_token: str = os.getenv("LICENSE_ADMIN_TOKEN", "").strip()
    port: int = int(os.getenv("LICENSE_PORT", "4349"))
    public_base_url: str = os.getenv("LICENSE_PUBLIC_BASE_URL", "https://licensing.mago-bot.com").rstrip("/")
    allowed_scopes: tuple[str, ...] = tuple(
        scope.strip()
        for scope in os.getenv(
            "LICENSE_ALLOWED_SCOPES",
            "whatsapp:connect,whatsapp:send,whatsapp:webhook,license:read,license:write",
        ).split(",")
        if scope.strip()
    )
