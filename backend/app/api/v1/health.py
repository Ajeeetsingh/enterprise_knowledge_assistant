"""Health and readiness endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.session import check_database_connection

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe — returns OK if the application process is running."""
    return HealthResponse(status="healthy")


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse | JSONResponse:
    """Readiness probe — verifies database connectivity."""
    if not check_database_connection():
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable"},
        )
    return ReadyResponse(status="ready")
