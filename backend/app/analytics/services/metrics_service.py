"""Time-series and KPI metrics for analytics dashboards (Phase 11)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.analytics.context import AnalyticsContext
from app.analytics.repositories.dashboard_repository import DashboardRepository
from app.analytics.utils.aggregation import bucket_counts_by_day
from app.analytics.utils.date_filters import (
    context_for_day,
    context_for_last_n_days,
    utc_end_of_day,
)


@dataclass(frozen=True)
class ActiveUserMetrics:
    """User activity KPIs for a reporting window."""

    daily_active_users: int
    weekly_active_users: int
    monthly_active_users: int


class AnalyticsMetricsService:
    """Compute derived metrics and activity series for dashboards."""

    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def get_active_user_metrics(
        self,
        *,
        context: AnalyticsContext | None = None,
    ) -> ActiveUserMetrics:
        """Return DAU/WAU/MAU based on distinct audit actors."""
        anchor_end = context.end_date if context is not None else utc_end_of_day()
        day_context = context_for_day(anchor_end)
        week_context = context_for_last_n_days(7, end=anchor_end)
        month_context = context_for_last_n_days(30, end=anchor_end)

        return ActiveUserMetrics(
            daily_active_users=self._repository.count_distinct_active_users(day_context),
            weekly_active_users=self._repository.count_distinct_active_users(week_context),
            monthly_active_users=self._repository.count_distinct_active_users(month_context),
        )

    def get_daily_event_series(
        self,
        event_type: str,
        context: AnalyticsContext,
    ) -> dict[str, int]:
        """Return daily event counts for charting."""
        timestamps = self._repository.list_event_timestamps(
            event_type=event_type,
            context=context,
        )
        return bucket_counts_by_day(timestamps)


def build_analytics_metrics_service(db: Session) -> AnalyticsMetricsService:
    """Construct a metrics service bound to the given database session."""
    return AnalyticsMetricsService(DashboardRepository(db))
