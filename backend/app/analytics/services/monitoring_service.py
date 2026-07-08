"""System monitoring orchestration for administrator dashboards (Phase 11.5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.analytics.repositories.monitoring_repository import MonitoringAnalyticsRepository
from app.analytics.schemas.common import ChartSeries
from app.analytics.utils.aggregation import average, bucket_counts_by_day
from app.services.metrics_service import build_metrics_service


ServiceHealthStatus = str


@dataclass(frozen=True)
class SystemHealthOverviewSnapshot:
    """Service-layer system health KPI snapshot."""

    api_health: ServiceHealthStatus
    database_health: ServiceHealthStatus
    search_service_health: ServiceHealthStatus
    vector_index_health: ServiceHealthStatus
    overall_system_status: ServiceHealthStatus
    uptime_seconds: int
    version: str
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class PerformanceMetricsSnapshot:
    """Service-layer performance metrics snapshot."""

    average_api_response_time_seconds: float | None
    average_search_time_seconds: float | None
    average_retrieval_time_seconds: float | None
    database_query_time_seconds: float | None
    embedding_generation_time_seconds: float | None
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class ResourceMetricsSnapshot:
    """Service-layer resource inventory snapshot."""

    total_documents: int
    total_users: int
    total_conversations: int
    storage_usage_bytes: int
    vector_index_size_bytes: int | None
    uploaded_file_count: int
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class ServiceStatusSnapshot:
    """Service-layer service status table snapshot."""

    items: list[dict[str, str]]
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class MonitoringTrendsSnapshot:
    """Service-layer operational trend series."""

    api_latency: ChartSeries
    search_latency: ChartSeries
    errors: ChartSeries
    health_events: ChartSeries
    timeline_items: list[dict[str, object]]
    timeline_total: int
    timeline_limit: int
    timeline_offset: int
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class HealthTimelineSnapshot:
    """Service-layer health timeline snapshot."""

    items: list[dict[str, object]]
    total: int
    limit: int
    offset: int
    start_date: datetime
    end_date: datetime


class SystemMonitoringAnalyticsService:
    """Aggregate operational health, performance, and resource metrics."""

    def __init__(self, repository: MonitoringAnalyticsRepository) -> None:
        self._repository = repository
        self._runtime_metrics = build_metrics_service()

    def get_overview(self, context: AnalyticsContext) -> SystemHealthOverviewSnapshot:
        """Return administrator KPIs for platform health."""
        uptime_seconds, version = self._runtime_metrics.get_runtime_info()
        database_health = self._status_from_connection(self._repository.is_database_connected())
        search_health = self._status_from_chat_failures(context)
        vector_health = self._status_from_retrieval_failures(context)
        components = [
            "healthy",
            database_health,
            search_health,
            vector_health,
        ]
        return SystemHealthOverviewSnapshot(
            api_health="healthy",
            database_health=database_health,
            search_service_health=search_health,
            vector_index_health=vector_health,
            overall_system_status=self._worst_status(components),
            uptime_seconds=uptime_seconds,
            version=version,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_performance(self, context: AnalyticsContext) -> PerformanceMetricsSnapshot:
        """Return performance metrics, using null when not instrumented."""
        latency_samples = [
            seconds for _, seconds in self._repository.compute_chat_latency_samples(context)
        ]
        avg_search = average(latency_samples)
        return PerformanceMetricsSnapshot(
            average_api_response_time_seconds=None,
            average_search_time_seconds=round(avg_search, 2) if avg_search is not None else None,
            average_retrieval_time_seconds=None,
            database_query_time_seconds=self._repository.measure_database_query_time_seconds(),
            embedding_generation_time_seconds=None,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_resources(self, context: AnalyticsContext) -> ResourceMetricsSnapshot:
        """Return platform resource inventory metrics."""
        return ResourceMetricsSnapshot(
            total_documents=self._repository.count_total_documents(),
            total_users=self._repository.count_total_users(),
            total_conversations=self._repository.count_total_conversations(),
            storage_usage_bytes=self._repository.sum_document_storage_bytes(),
            vector_index_size_bytes=None,
            uploaded_file_count=self._repository.count_uploaded_files(),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_services(self, context: AnalyticsContext) -> ServiceStatusSnapshot:
        """Return current service health statuses."""
        probes = self._repository.probe_service_statuses(context)
        return ServiceStatusSnapshot(
            items=[
                {
                    "service": probe.service,
                    "status": probe.status,
                    "detail": probe.detail,
                }
                for probe in probes
            ],
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_trends(
        self,
        context: AnalyticsContext,
        *,
        limit: int = 10,
        offset: int = 0,
    ) -> MonitoringTrendsSnapshot:
        """Return operational trend series for the selected reporting window."""
        latency_samples = self._repository.compute_chat_latency_samples(context)
        timeline = self.get_health_timeline(context, limit=limit, offset=offset)
        return MonitoringTrendsSnapshot(
            api_latency=self._series("api_latency", {}),
            search_latency=self._series(
                "search_latency",
                self._bucket_average_latencies(latency_samples),
            ),
            errors=self._series(
                AnalyticsEvents.CHAT_FAILURE,
                bucket_counts_by_day(self._repository.list_error_event_timestamps(context)),
            ),
            health_events=self._series(
                "health_events",
                bucket_counts_by_day(self._repository.list_health_event_timestamps(context)),
            ),
            timeline_items=timeline.items,
            timeline_total=timeline.total,
            timeline_limit=timeline.limit,
            timeline_offset=timeline.offset,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_health_timeline(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> HealthTimelineSnapshot:
        """Return recent health-related audit events."""
        rows, total = self._repository.list_health_events(
            context,
            limit=limit,
            offset=offset,
        )
        return HealthTimelineSnapshot(
            items=[
                {
                    "timestamp": row.timestamp,
                    "service": row.service,
                    "status": row.status,
                    "event_type": row.event_type,
                    "detail": row.detail,
                }
                for row in rows
            ],
            total=total,
            limit=limit,
            offset=offset,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    @staticmethod
    def _series(event_type: str, points: dict[str, float | int]) -> ChartSeries:
        normalized = {key: int(value) for key, value in points.items()}
        return ChartSeries(event_type=event_type, points=normalized)

    @staticmethod
    def _bucket_average_latencies(
        samples: list[tuple[datetime, float]],
    ) -> dict[str, int]:
        if not samples:
            return {}
        buckets: dict[str, list[float]] = {}
        for timestamp, seconds in samples:
            day = timestamp.astimezone(UTC).date().isoformat()
            buckets.setdefault(day, []).append(seconds)
        return {
            day: int(round(sum(values) / len(values)))
            for day, values in sorted(buckets.items())
        }

    @staticmethod
    def _status_from_connection(connected: bool) -> ServiceHealthStatus:
        return "healthy" if connected else "unavailable"

    def _status_from_chat_failures(self, context: AnalyticsContext) -> ServiceHealthStatus:
        responses = self._repository.count_chat_responses(context)
        failures = self._repository.count_chat_failures(context)
        return self._status_from_failure_rate(failures, responses + failures)

    def _status_from_retrieval_failures(self, context: AnalyticsContext) -> ServiceHealthStatus:
        questions = self._repository.count_chat_questions(context)
        failures = self._repository.count_chat_failures(context)
        return self._status_from_failure_rate(failures, questions)

    @staticmethod
    def _status_from_failure_rate(failures: int, attempts: int) -> ServiceHealthStatus:
        if attempts == 0:
            return "healthy"
        rate = failures / attempts
        if rate >= 0.5:
            return "unavailable"
        if rate >= 0.2:
            return "degraded"
        return "healthy"

    @staticmethod
    def _worst_status(statuses: list[ServiceHealthStatus]) -> ServiceHealthStatus:
        priority = {"unavailable": 3, "degraded": 2, "healthy": 1}
        return max(statuses, key=lambda status: priority.get(status, 0))


def build_system_monitoring_analytics_service(
    db: Session,
) -> SystemMonitoringAnalyticsService:
    """Construct a system monitoring analytics service bound to *db*."""
    return SystemMonitoringAnalyticsService(MonitoringAnalyticsRepository(db))
