"""Administrator error analytics API (Phase 11.6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analytics.analytics_dependencies import (
    get_error_analytics_service,
    parse_analytics_filter,
    resolve_analytics_context,
    resolve_user_list_limit,
)
from app.analytics.context import AnalyticsContext
from app.analytics.schemas.error import (
    EndpointFailureResponse,
    ErrorCategoryResponse,
    ErrorOverviewResponse,
    ErrorTrendsResponse,
    FailureAnalysisResponse,
)
from app.analytics.schemas.filters import AnalyticsFilter
from app.analytics.services.error_analytics_service import ErrorAnalyticsService
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
        "description": "Only administrators may access analytics data.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Invalid analytics parameters.",
    },
}


@router.get(
    "/overview",
    response_model=ErrorOverviewResponse,
    summary="Get error analytics overview",
    description=(
        "Return administrator KPIs for operational failures including "
        "authentication, authorization, retrieval, and overall error rates."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_error_overview(
    _: User = Depends(require_audit_admin),
    service: ErrorAnalyticsService = Depends(get_error_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> ErrorOverviewResponse:
    """Return error analytics KPI summary."""
    return ErrorOverviewResponse.from_snapshot(service.get_overview(context))


@router.get(
    "/trends",
    response_model=ErrorTrendsResponse,
    summary="Get error trends",
    description=(
        "Return time-series data for total errors, authentication failures, "
        "retrieval failures, upload failures, and permission denials."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_error_trends(
    _: User = Depends(require_audit_admin),
    service: ErrorAnalyticsService = Depends(get_error_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> ErrorTrendsResponse:
    """Return error trend series."""
    return ErrorTrendsResponse.from_snapshot(service.get_trends(context))


@router.get(
    "/categories",
    response_model=ErrorCategoryResponse,
    summary="Get error category breakdown",
    description=(
        "Return error counts grouped by category and service, plus recurring "
        "error patterns for the selected reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_error_categories(
    _: User = Depends(require_audit_admin),
    service: ErrorAnalyticsService = Depends(get_error_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> ErrorCategoryResponse:
    """Return error category breakdown."""
    limit = resolve_user_list_limit(filters)
    return ErrorCategoryResponse.from_snapshot(
        service.get_categories(context, limit=limit, offset=filters.offset),
    )


@router.get(
    "/endpoints",
    response_model=EndpointFailureResponse,
    summary="Get endpoint failure analytics",
    description=(
        "Return frequently failing endpoints or resources derived from "
        "persisted audit metadata."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_endpoint_failures(
    _: User = Depends(require_audit_admin),
    service: ErrorAnalyticsService = Depends(get_error_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> EndpointFailureResponse:
    """Return endpoint failure analytics."""
    limit = resolve_user_list_limit(filters)
    return EndpointFailureResponse.from_snapshot(
        service.get_endpoints(context, limit=limit, offset=filters.offset),
    )


@router.get(
    "/failures",
    response_model=FailureAnalysisResponse,
    summary="Get failure analysis",
    description=(
        "Return measurable failure analysis for operations, retrieval, "
        "upload, and authentication events."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_failure_analysis(
    _: User = Depends(require_audit_admin),
    service: ErrorAnalyticsService = Depends(get_error_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> FailureAnalysisResponse:
    """Return failure analysis sections."""
    limit = resolve_user_list_limit(filters)
    return FailureAnalysisResponse.from_snapshot(
        service.get_failures(context, limit=limit, offset=filters.offset),
    )
