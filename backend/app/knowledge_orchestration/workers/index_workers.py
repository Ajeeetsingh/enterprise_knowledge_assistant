"""Workers that wrap existing IndexProviders without duplicating lookup logic."""

from __future__ import annotations

from typing import Any

from app.knowledge_execution.providers.base import IndexProvider
from app.knowledge_execution.providers.catalog import PROVIDER_TYPES, build_providers
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_orchestration.models.types import (
    WorkerCapability,
    WorkerEvidence,
    WorkerHealth,
    utc_now_iso,
)
from app.knowledge_orchestration.workers.base import Worker
from app.query_planner.models.types import QueryExecutionPlan

# Priority: metadata/collection/department first, graph last
_PRIORITIES = {
    "metadata": 10,
    "collection": 20,
    "department": 20,
    "taxonomy": 30,
    "keyword": 40,
    "topic": 40,
    "tag": 45,
    "entity": 50,
    "relationship": 60,
    "version": 55,
}


class IndexProviderWorker(Worker):
    """Thin wrapper around an existing IndexProvider."""

    def __init__(self, provider: IndexProvider) -> None:
        self._provider = provider

    def id(self) -> str:
        return self._provider.name

    def capabilities(self) -> list[WorkerCapability]:
        return [
            WorkerCapability(
                name=f"index:{self._provider.name}",
                description=f"Wraps Hybrid Knowledge Index provider '{self._provider.name}'",
            )
        ]

    def supports(self, plan: QueryExecutionPlan) -> bool:
        required = set(plan.required_indexes or [])
        if not required:
            return self.id() in {"keyword", "metadata"}
        return self.id() in required

    def execute(self, plan: QueryExecutionPlan, *, context: dict[str, Any] | None = None) -> WorkerEvidence:
        try:
            result = self._provider.execute(plan)
            return WorkerEvidence(
                worker_id=self.id(),
                success=result.success,
                evidence_items=[item.to_dict() for item in result.evidence],
                elapsed_ms=result.elapsed_ms,
                error=result.error,
                diagnostics={"query_used": result.query_used, "provider": self._provider.name},
                source_attribution=f"index_provider:{self._provider.name}",
            )
        except Exception as exc:  # noqa: BLE001
            return WorkerEvidence(
                worker_id=self.id(),
                success=False,
                error=type(exc).__name__,
                diagnostics={"exception": str(exc)},
                source_attribution=f"index_provider:{self._provider.name}",
            )

    def health(self) -> WorkerHealth:
        return WorkerHealth(
            status="healthy",
            detail=f"provider={self._provider.name}",
            checked_at=utc_now_iso(),
        )

    def priority(self) -> int:
        return _PRIORITIES.get(self.id(), 100)


def build_index_workers(manager: KnowledgeIndexManager | None = None) -> list[IndexProviderWorker]:
    managers = manager or KnowledgeIndexManager()
    providers = build_providers(managers)
    # Preserve catalog order
    return [IndexProviderWorker(providers[name]) for name in PROVIDER_TYPES if name in providers]
