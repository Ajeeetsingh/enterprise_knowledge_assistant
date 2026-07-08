"""Administrator user analytics API (Phase 11.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analytics.analytics_dependencies import (
    get_user_analytics_service,
    parse_analytics_filter,
    resolve_analytics_context,
    resolve_user_list_limit,
)
from app.analytics.context import AnalyticsContext
from app.analytics.schemas.filters import AnalyticsFilter
from app.analytics.schemas.user import (
    PaginatedUserActivityResponse,
    UserActivityResponse,
    UserAnalyticsOverviewResponse,
    UserGrowthTrendsResponse,
)
from app.analytics.services.user_analytics_service import UserAnalyticsService
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
    response_model=UserAnalyticsOverviewResponse,
    summary="Get user analytics overview",
    description=(
        "Return administrator KPIs for user adoption and engagement including "
        "DAU, WAU, MAU, and average activity metrics."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_user_analytics_overview(
    _: User = Depends(require_audit_admin),
    service: UserAnalyticsService = Depends(get_user_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> UserAnalyticsOverviewResponse:
    """Return user analytics KPI summary."""
    return UserAnalyticsOverviewResponse.from_snapshot(service.get_overview(context))


@router.get(
    "/trends",
    response_model=UserGrowthTrendsResponse,
    summary="Get user growth trends",
    description=(
        "Return time-series data for user registrations, active users, logins, "
        "conversations, and questions asked."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_user_growth_trends(
    _: User = Depends(require_audit_admin),
    service: UserAnalyticsService = Depends(get_user_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> UserGrowthTrendsResponse:
    """Return user growth trend series."""
    return UserGrowthTrendsResponse.from_snapshot(service.get_trends(context))


@router.get(
    "/activity",
    response_model=UserActivityResponse,
    summary="Get user activity analytics",
    description=(
        "Return engagement metrics and activity trend series for the selected "
        "reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_user_activity_analytics(
    _: User = Depends(require_audit_admin),
    service: UserAnalyticsService = Depends(get_user_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
) -> UserActivityResponse:
    """Return user engagement and activity trends."""
    return UserActivityResponse.from_snapshot(service.get_activity(context))


@router.get(
    "/top-users",
    response_model=PaginatedUserActivityResponse,
    summary="Get top active users",
    description="Return users ranked by question activity in the reporting window.",
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_top_active_users(
    _: User = Depends(require_audit_admin),
    service: UserAnalyticsService = Depends(get_user_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> PaginatedUserActivityResponse:
    """Return top active users."""
    limit = resolve_user_list_limit(filters)
    rows, total = service.get_top_users(context, limit=limit, offset=filters.offset)
    return PaginatedUserActivityResponse.from_rows(
        rows,
        total=total,
        limit=limit,
        offset=filters.offset,
    )


@router.get(
    "/inactive",
    response_model=PaginatedUserActivityResponse,
    summary="Get inactive users",
    description=(
        "Return active accounts with no audit activity during the reporting window."
    ),
    responses=_ANALYTICS_ERROR_RESPONSES,
)
def get_inactive_users(
    _: User = Depends(require_audit_admin),
    service: UserAnalyticsService = Depends(get_user_analytics_service),
    context: AnalyticsContext = Depends(resolve_analytics_context),
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> PaginatedUserActivityResponse:
    """Return inactive users."""
    limit = resolve_user_list_limit(filters)
    rows, total = service.get_inactive_users(
        context,
        limit=limit,
        offset=filters.offset,
    )
    return PaginatedUserActivityResponse.from_rows(
        rows,
        total=total,
        limit=limit,
        offset=filters.offset,
    )
