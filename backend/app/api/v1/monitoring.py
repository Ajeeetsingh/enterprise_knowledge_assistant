"""Administrator monitoring and metrics API (Phase 7.7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_audit_admin
from app.db.models import User
from app.schemas.errors import ErrorResponse
from app.schemas.monitoring import MonitoringSummaryResponse, SystemMetricsResponse
from app.services.metrics_service import MetricsService
from app.services.monitoring_dependencies import get_metrics_service, get_monitoring_service
from app.services.monitoring_service import MonitoringService

router = APIRouter()

_MONITORING_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Only administrators may access monitoring data.",
    },
}


@router.get(
    "/summary",
    response_model=MonitoringSummaryResponse,
    summary="Get monitoring summary",
    description=(
        "Return aggregated business metrics for operational visibility. "
        "Only administrators and superusers may access monitoring data."
    ),
    responses=_MONITORING_ERROR_RESPONSES,
)
def get_monitoring_summary(
    _: User = Depends(require_audit_admin),
    monitoring_service: MonitoringService = Depends(get_monitoring_service),
) -> MonitoringSummaryResponse:
    """Return platform activity and inventory counts."""
    return MonitoringSummaryResponse.from_summary(monitoring_service.get_summary())


@router.get(
    "/metrics",
    response_model=SystemMetricsResponse,
    summary="Get system metrics",
    description=(
        "Return lightweight runtime metrics such as uptime and database connectivity. "
        "Only administrators and superusers may access monitoring data."
    ),
    responses=_MONITORING_ERROR_RESPONSES,
)
def get_system_metrics(
    _: User = Depends(require_audit_admin),
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> SystemMetricsResponse:
    """Return process-level metrics."""
    return SystemMetricsResponse.from_metrics(metrics_service.get_metrics())
