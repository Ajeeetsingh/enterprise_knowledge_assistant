"""Administrator system monitoring analytics API (Phase 11.5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analytics.analytics_dependencies import (
    get_system_monitoring_analytics_service,
    parse_analytics_filter,
    resolve_analytics_context,
    resolve_user_list_limit,
)
from app.analytics.context import AnalyticsContext
from app.analytics.schemas.filters import AnalyticsFilter
from app.analytics.schemas.monitoring import (
    MonitoringTrendsResponse,
    PerformanceMetricsResponse,
    ResourceMetricsResponse,
    ServiceStatusResponse,
    SystemHealthOverviewResponse,
)
from app.analytics.services.monitoring_service import SystemMonitoringAnalyticsService
from app.auth.dependencies import require_audit_admin
from app.db.models import User
from app.schemas.errors import ErrorResponse

router = APIRouter()

_ANALYTICS_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Only administrators may access monitoring data.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Invalid analytics parameters.",
    },
}


@router.get(
    "/overview",
    response_model=SystemHealthOverviewResponse,
    summary="Get system monitoring overview",
    description=(
        "Return administrator KPIs for API, database, search, vector index, "
        "and overall platform health."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_system_monitoring_overview(
    _: User = Depends(require_audit_admin),
    service: SystemMonitoringAnalyticsService = Depends(get_system_monitoring_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> SystemHealthOverviewResponse:
    """Return system health KPI summary."""
    return SystemHealthOverviewResponse.from_snapshot(service.get_overview(context))


@router.get(
    "/performance",
    response_model=PerformanceMetricsResponse,
    summary="Get performance metrics",
    description=(
        "Return operational performance metrics. Uninstrumented metrics are "
        "returned as null rather than fabricated values."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_performance_metrics(
    _: User = Depends(require_audit_admin),
    service: SystemMonitoringAnalyticsService = Depends(get_system_monitoring_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> PerformanceMetricsResponse:
    """Return performance metrics."""
    return PerformanceMetricsResponse.from_snapshot(service.get_performance(context))


@router.get(
    "/resources",
    response_model=ResourceMetricsResponse,
    summary="Get resource metrics",
    description="Return platform inventory and storage usage metrics.",
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_resource_metrics(
    _: User = Depends(require_audit_admin),
    service: SystemMonitoringAnalyticsService = Depends(get_system_monitoring_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> ResourceMetricsResponse:
    """Return resource metrics."""
    return ResourceMetricsResponse.from_snapshot(service.get_resources(context))


@router.get(
    "/services",
    response_model=ServiceStatusResponse,
    summary="Get service status",
    description="Return current health status for platform services.",
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_service_status(
    _: User = Depends(require_audit_admin),
    service: SystemMonitoringAnalyticsService = Depends(get_system_monitoring_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> ServiceStatusResponse:
    """Return service status table data."""
    return ServiceStatusResponse.from_snapshot(service.get_services(context))


@router.get(
    "/trends",
    response_model=MonitoringTrendsResponse,
    summary="Get monitoring trends",
    description=(
        "Return operational trend series for latency, errors, and health "
        "events over the selected reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_monitoring_trends(
    _: User = Depends(require_audit_admin),
    service: SystemMonitoringAnalyticsService = Depends(get_system_monitoring_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> MonitoringTrendsResponse:
    """Return monitoring trend series and health timeline."""
    limit = resolve_user_list_limit(filters)
    return MonitoringTrendsResponse.from_snapshot(
        service.get_trends(context, limit=limit, offset=filters.offset),
    )
