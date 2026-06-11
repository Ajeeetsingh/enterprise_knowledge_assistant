"""Application configuration via environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central settings for the Enterprise Knowledge Assistant backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Enterprise Knowledge Assistant"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = False

    # Database
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/eka"
    )

    # Logging
    log_level: str = "INFO"

    # Single-tenant MVP placeholder
    tenant_id: str = "default"

    # Local filesystem storage (MVP)
    storage_path: Path = BACKEND_ROOT / "storage"
    documents_path: Path = BACKEND_ROOT / "storage" / "documents"
    indexes_path: Path = BACKEND_ROOT / "storage" / "indexes"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Reserved for Phase 2 (auth) — loaded but unused in Phase 1
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
