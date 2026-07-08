"""Pydantic models for system monitoring analytics APIs (Phase 11.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.schemas.common import ChartSeries

ServiceHealthStatus = Literal["healthy", "degraded", "unavailable"]

if TYPE_CHECKING:
    from app.analytics.services.monitoring_service import (
        HealthTimelineSnapshot,
        MonitoringTrendsSnapshot,
        PerformanceMetricsSnapshot,
        ResourceMetricsSnapshot,
        ServiceStatusSnapshot,
        SystemHealthOverviewSnapshot,
    )


class SystemHealthOverviewResponse(BaseModel):
    """Administrator KPI summary for platform health."""

    model_config = ConfigDict(from_attributes=True)

    api_health: ServiceHealthStatus
    database_health: ServiceHealthStatus
    search_service_health: ServiceHealthStatus
    vector_index_health: ServiceHealthStatus
    overall_system_status: ServiceHealthStatus
    uptime_seconds: int = Field(ge=0)
    version: str
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(
        cls,
        snapshot: SystemHealthOverviewSnapshot,
    ) -> SystemHealthOverviewResponse:
        """Build an API response from a service-layer overview."""
        return cls.model_validate(snapshot)


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics for operational dashboards.

    ``average_api_response_time_seconds``, ``average_retrieval_time_seconds``,
    and ``embedding_generation_time_seconds`` are null until request-level
    instrumentation is added. ``average_search_time_seconds`` is estimated
    from chat turn latency when message pairs exist.
    """

    model_config = ConfigDict(from_attributes=True)

    average_api_response_time_seconds: float | None = Field(default=None, ge=0.0)
    average_search_time_seconds: float | None = Field(default=None, ge=0.0)
    average_retrieval_time_seconds: float | None = Field(default=None, ge=0.0)
    database_query_time_seconds: float | None = Field(default=None, ge=0.0)
    embedding_generation_time_seconds: float | None = Field(default=None, ge=0.0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: PerformanceMetricsSnapshot) -> PerformanceMetricsResponse:
        """Build an API response from a service-layer performance snapshot."""
        return cls.model_validate(snapshot)


class ResourceMetricsResponse(BaseModel):
    """Resource inventory metrics for operational dashboards."""

    model_config = ConfigDict(from_attributes=True)

    total_documents: int = Field(ge=0)
    total_users: int = Field(ge=0)
    total_conversations: int = Field(ge=0)
    storage_usage_bytes: int = Field(ge=0)
    vector_index_size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Not instrumented; returns null until vector store metrics are exposed.",
    )
    uploaded_file_count: int = Field(ge=0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: ResourceMetricsSnapshot) -> ResourceMetricsResponse:
        """Build an API response from a service-layer resource snapshot."""
        return cls.model_validate(snapshot)


class ServiceStatusItemResponse(BaseModel):
    """Single service health status row."""

    service: str
    status: ServiceHealthStatus
    detail: str


class ServiceStatusResponse(BaseModel):
    """Current service health statuses."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ServiceStatusItemResponse]
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: ServiceStatusSnapshot) -> ServiceStatusResponse:
        """Build an API response from a service-layer service status snapshot."""
        return cls(
            items=[
                ServiceStatusItemResponse(
                    service=str(item["service"]),
                    status=item["status"],  # type: ignore[arg-type]
                    detail=str(item["detail"]),
                )
                for item in snapshot.items
            ],
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )


class HealthTimelineItemResponse(BaseModel):
    """Single health timeline event."""

    timestamp: datetime
    service: str
    status: ServiceHealthStatus
    event_type: str
    detail: str


class MonitoringTrendsResponse(BaseModel):
    """Operational trend series for monitoring dashboards."""

    model_config = ConfigDict(from_attributes=True)

    api_latency: ChartSeries
    search_latency: ChartSeries
    errors: ChartSeries
    health_events: ChartSeries
    timeline_items: list[HealthTimelineItemResponse]
    timeline_total: int = Field(ge=0)
    timeline_limit: int = Field(ge=1)
    timeline_offset: int = Field(ge=0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: MonitoringTrendsSnapshot) -> MonitoringTrendsResponse:
        """Build an API response from a service-layer trends snapshot."""
        return cls(
            api_latency=snapshot.api_latency,
            search_latency=snapshot.search_latency,
            errors=snapshot.errors,
            health_events=snapshot.health_events,
            timeline_items=[
                HealthTimelineItemResponse(
                    timestamp=item["timestamp"],  # type: ignore[arg-type]
                    service=str(item["service"]),
                    status=item["status"],  # type: ignore[arg-type]
                    event_type=str(item["event_type"]),
                    detail=str(item["detail"]),
                )
                for item in snapshot.timeline_items
            ],
            timeline_total=snapshot.timeline_total,
            timeline_limit=snapshot.timeline_limit,
            timeline_offset=snapshot.timeline_offset,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )


class HealthTimelineResponse(BaseModel):
    """Recent operational health events."""

    model_config = ConfigDict(from_attributes=True)

    items: list[HealthTimelineItemResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: HealthTimelineSnapshot) -> HealthTimelineResponse:
        """Build an API response from a service-layer timeline snapshot."""
        return cls(
            items=[
                HealthTimelineItemResponse(
                    timestamp=item["timestamp"],  # type: ignore[arg-type]
                    service=str(item["service"]),
                    status=item["status"],  # type: ignore[arg-type]
                    event_type=str(item["event_type"]),
                    detail=str(item["detail"]),
                )
                for item in snapshot.items
            ],
            total=snapshot.total,
            limit=snapshot.limit,
            offset=snapshot.offset,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )
