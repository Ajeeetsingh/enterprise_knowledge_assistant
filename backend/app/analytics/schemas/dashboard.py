"""Dashboard overview API schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.schemas.common import MetricSummary

if TYPE_CHECKING:
    from app.analytics.services.dashboard_service import DashboardOverviewSnapshot


class DashboardInventory(BaseModel):
    """Static platform inventory counts."""

    model_config = ConfigDict(from_attributes=True)

    total_users: int = Field(ge=0)
    active_users: int = Field(ge=0)
    total_documents: int = Field(ge=0)
    total_conversations: int = Field(ge=0)


class DashboardCard(BaseModel):
    """Single KPI card for administrator dashboards."""

    label: str
    value: str | int | float


class DashboardOverview(BaseModel):
    """Combined dashboard metrics for administrators."""

    inventory: DashboardInventory
    chat_metrics: MetricSummary
    security_events: int = Field(ge=0)
    audit_events: int = Field(ge=0)


class DashboardResponse(DashboardOverview):
    """Public dashboard API response."""

    @classmethod
    def from_snapshot(
        cls,
        overview: DashboardOverviewSnapshot,
    ) -> DashboardResponse:
        """Build an API response from a service-layer overview."""
        return cls(
            inventory=DashboardInventory.model_validate(overview.inventory),
            chat_metrics=MetricSummary.from_snapshot(overview.chat_metrics),
            security_events=overview.security_events,
            audit_events=overview.audit_events,
        )
