"""Pydantic models for monitoring and metrics APIs (Phase 7.7)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.services.metrics_service import SystemMetrics
from app.services.monitoring_service import MonitoringSummary


class MonitoringSummaryResponse(BaseModel):
    """Business metrics summary for administrators."""

    model_config = ConfigDict(from_attributes=True)

    total_users: int = Field(ge=0)
    active_users: int = Field(ge=0)
    total_documents: int = Field(ge=0)
    total_conversations: int = Field(ge=0)
    questions_today: int = Field(ge=0)
    failed_logins_today: int = Field(ge=0)
    audit_events_today: int = Field(ge=0)

    @classmethod
    def from_summary(cls, summary: MonitoringSummary) -> MonitoringSummaryResponse:
        """Build an API response from a service-layer summary."""
        return cls.model_validate(summary)


class SystemMetricsResponse(BaseModel):
    """Runtime metrics for administrators."""

    model_config = ConfigDict(from_attributes=True)

    uptime_seconds: int = Field(ge=0)
    database_connected: bool
    version: str

    @classmethod
    def from_metrics(cls, metrics: SystemMetrics) -> SystemMetricsResponse:
        """Build an API response from service-layer metrics."""
        return cls.model_validate(metrics)
