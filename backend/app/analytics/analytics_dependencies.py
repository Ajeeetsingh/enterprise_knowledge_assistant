"""FastAPI dependencies for analytics APIs (Phase 11)."""

from __future__ import annotations

from datetime import datetime

from fastapi import Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.analytics.context import AnalyticsContext
from app.analytics.schemas.filters import AnalyticsFilter, DateRangePreset, GroupBy
from app.analytics.services.ai_analytics_service import (
    AIAnalyticsService,
    build_ai_analytics_service,
)
from app.analytics.services.knowledge_analytics_service import (
    KnowledgeAnalyticsService,
    build_knowledge_analytics_service,
)
from app.analytics.services.error_analytics_service import (
    ErrorAnalyticsService,
    build_error_analytics_service,
)
from app.analytics.services.monitoring_service import (
    SystemMonitoringAnalyticsService,
    build_system_monitoring_analytics_service,
)
from app.analytics.services.reporting_service import ReportingService, build_reporting_service
from app.analytics.services.user_analytics_service import (
    UserAnalyticsService,
    build_user_analytics_service,
)
from app.analytics.utils.date_filters import context_from_filter
from app.db.session import get_db

DEFAULT_USER_ANALYTICS_LIMIT = 10
MAX_USER_ANALYTICS_LIMIT = 100


def get_ai_analytics_service(
    db: Session = Depends(get_db),
) -> AIAnalyticsService:
    """Return an AI analytics service bound to the current database session."""
    return build_ai_analytics_service(db)


def get_knowledge_analytics_service(
    db: Session = Depends(get_db),
) -> KnowledgeAnalyticsService:
    """Return a knowledge analytics service bound to the current database session."""
    return build_knowledge_analytics_service(db)


def get_error_analytics_service(
    db: Session = Depends(get_db),
) -> ErrorAnalyticsService:
    """Return an error analytics service bound to the current database session."""
    return build_error_analytics_service(db)


def get_system_monitoring_analytics_service(
    db: Session = Depends(get_db),
) -> SystemMonitoringAnalyticsService:
    """Return a system monitoring analytics service bound to the current session."""
    return build_system_monitoring_analytics_service(db)


def get_user_analytics_service(
    db: Session = Depends(get_db),
) -> UserAnalyticsService:
    """Return a user analytics service bound to the current database session."""
    return build_user_analytics_service(db)


def get_reporting_service(
    db: Session = Depends(get_db),
) -> ReportingService:
    """Return a reporting service bound to the current database session."""
    return build_reporting_service(db)


def parse_analytics_filter(
    range_preset: DateRangePreset | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    timezone: str = Query(default="UTC", min_length=1, max_length=64),
    group_by: GroupBy | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=365),
    offset: int = Query(default=0, ge=0),
) -> AnalyticsFilter:
    """Parse and validate analytics query parameters."""
    try:
        return AnalyticsFilter(
            range_preset=range_preset,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone,
            group_by=group_by,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid analytics parameters.",
        ) from exc


def resolve_analytics_context(
    filters: AnalyticsFilter = Depends(parse_analytics_filter),
) -> AnalyticsContext:
    """Convert API filters into an ``AnalyticsContext``."""
    try:
        return context_from_filter(filters, default_days=7)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


def resolve_user_list_limit(filters: AnalyticsFilter) -> int:
    """Return a bounded page size for user list endpoints."""
    if filters.limit is None:
        return DEFAULT_USER_ANALYTICS_LIMIT
    return min(filters.limit, MAX_USER_ANALYTICS_LIMIT)
