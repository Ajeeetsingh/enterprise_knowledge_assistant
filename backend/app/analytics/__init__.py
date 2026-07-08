"""Analytics module — aggregated business insights (Phase 11).

Audit logs record events; analytics aggregates them into dashboard KPIs.
Runtime process metrics remain in ``app.services.metrics_service``.
Operational summaries from Phase 7.7 remain in ``app.services.monitoring_service``.
"""

from app.analytics.context import AnalyticsContext
from app.analytics.services.dashboard_service import DashboardService, build_dashboard_service
from app.analytics.services.metrics_service import AnalyticsMetricsService, build_analytics_metrics_service

__all__ = [
    "AnalyticsContext",
    "AnalyticsMetricsService",
    "DashboardService",
    "build_analytics_metrics_service",
    "build_dashboard_service",
]
