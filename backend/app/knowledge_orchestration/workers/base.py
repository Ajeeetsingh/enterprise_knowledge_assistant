"""Common Worker interface for the orchestration framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.knowledge_orchestration.models.types import (
    WorkerCapability,
    WorkerEvidence,
    WorkerHealth,
    utc_now_iso,
)
from app.query_planner.models.types import QueryExecutionPlan


class Worker(ABC):
    """Discoverable execution worker. Not an autonomous AI agent."""

    @abstractmethod
    def id(self) -> str:
        """Stable worker identifier."""

    @abstractmethod
    def capabilities(self) -> list[WorkerCapability]:
        """Declare what this worker can contribute."""

    @abstractmethod
    def supports(self, plan: QueryExecutionPlan) -> bool:
        """Return True when this worker is eligible for the plan."""

    @abstractmethod
    def execute(self, plan: QueryExecutionPlan, *, context: dict[str, Any] | None = None) -> WorkerEvidence:
        """Execute against the plan. Must never raise into the orchestrator."""

    def health(self) -> WorkerHealth:
        return WorkerHealth(status="healthy", detail="ok", checked_at=utc_now_iso())

    def priority(self) -> int:
        """Lower number = higher priority."""
        return 100

    def diagnostics(self) -> dict[str, Any]:
        return {
            "id": self.id(),
            "priority": self.priority(),
            "capabilities": [item.to_dict() for item in self.capabilities()],
            "health": self.health().to_dict(),
        }

    def depends_on(self) -> list[str]:
        """Optional worker ids that should complete before this worker."""
        return []
