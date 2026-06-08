"""Health and readiness endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.db.session import check_database_connection

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str


class ReadyResponse(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe — returns OK if the application process is running."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    """Readiness probe — verifies database connectivity."""
    db_ok = check_database_connection()
    return ReadyResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unavailable",
    )
