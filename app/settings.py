from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    onec_base_url: str
    onec_basic_user: str
    onec_basic_pass: str
    onec_api_key: str
    # Иногда 1C дополнительно требует эти ключи (в разных названиях).
    onec_secret_key: str = ""
    onec_app_key: str = ""

    cors_allow_origins: str = ""

    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    cache_ttl_seconds: int = 30
    http_timeout_seconds: float = 15.0

    log_level: str = "INFO"
    debug_upstream_errors: bool = False

    def cors_origins_list(self) -> list[str]:
        raw = (self.cors_allow_origins or "").strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


settings = Settings()

