"""Dashboard orchestration for administrator overview APIs (Phase 11)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.analytics.repositories.dashboard_repository import (
    ChatAnalyticsSnapshot,
    DashboardRepository,
)
from app.analytics.utils.date_filters import default_dashboard_context


@dataclass(frozen=True)
class DashboardInventorySnapshot:
    """Current platform inventory snapshot."""

    total_users: int
    active_users: int
    total_documents: int
    total_conversations: int


@dataclass(frozen=True)
class DashboardOverviewSnapshot:
    """Aggregated dashboard metrics for a reporting window."""

    inventory: DashboardInventorySnapshot
    chat_metrics: ChatAnalyticsSnapshot
    security_events: int
    audit_events: int


class DashboardService:
    """Aggregate audit and inventory data into dashboard insights."""

    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def get_inventory(self) -> DashboardInventorySnapshot:
        """Return current platform inventory counts."""
        return DashboardInventorySnapshot(
            total_users=self._repository.count_users(active_only=False),
            active_users=self._repository.count_users(active_only=True),
            total_documents=self._repository.count_documents(),
            total_conversations=self._repository.count_conversations(),
        )

    def get_overview(
        self,
        context: AnalyticsContext | None = None,
    ) -> DashboardOverviewSnapshot:
        """Return a dashboard overview for the given reporting window."""
        window = context or default_dashboard_context()
        chat_metrics = self._repository.get_chat_snapshot(window)

        return DashboardOverviewSnapshot(
            inventory=self.get_inventory(),
            chat_metrics=chat_metrics,
            security_events=self._repository.count_audit_events(
                event_type=AnalyticsEvents.SECURITY_PERMISSION_DENIED,
                context=window,
            ),
            audit_events=self._repository.count_audit_events(context=window),
        )


def build_dashboard_service(db: Session) -> DashboardService:
    """Construct a dashboard service bound to the given database session."""
    return DashboardService(DashboardRepository(db))
