"""Analytics API schemas."""

from app.analytics.schemas.common import ChartSeries, MetricSummary, TimeSeries
from app.analytics.schemas.dashboard import (
    DashboardCard,
    DashboardInventory,
    DashboardOverview,
    DashboardResponse,
)
from app.analytics.schemas.filters import AnalyticsFilter, DateRange, DateRangePreset, GroupBy
from app.analytics.schemas.user import (
    PaginatedUserActivityResponse,
    UserActivityItemResponse,
    UserActivityResponse,
    UserAnalyticsOverviewResponse,
    UserGrowthTrendsResponse,
)

__all__ = [
    "AnalyticsFilter",
    "ChartSeries",
    "DashboardCard",
    "DashboardInventory",
    "DashboardOverview",
    "DashboardResponse",
    "DateRange",
    "DateRangePreset",
    "GroupBy",
    "MetricSummary",
    "PaginatedUserActivityResponse",
    "TimeSeries",
    "UserActivityItemResponse",
    "UserActivityResponse",
    "UserAnalyticsOverviewResponse",
    "UserGrowthTrendsResponse",
]
