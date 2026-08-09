"""Graph worker wrapping existing GraphProvider (no duplicated graph logic)."""

from __future__ import annotations

from typing import Any

from app.knowledge_execution.models.types import CandidateEvidenceSet, CandidateDocument
from app.knowledge_graph.providers.graph_provider import GraphProvider
from app.knowledge_graph.services.graph_service import KnowledgeGraphService
from app.knowledge_orchestration.models.types import (
    WorkerCapability,
    WorkerEvidence,
    WorkerHealth,
    utc_now_iso,
)
from app.knowledge_orchestration.workers.base import Worker
from app.query_planner.models.types import QueryExecutionPlan


class GraphWorker(Worker):
    def __init__(
        self,
        graph_provider: GraphProvider | None = None,
        graph_service: KnowledgeGraphService | None = None,
    ) -> None:
        service = graph_service or KnowledgeGraphService()
        self._provider = graph_provider or GraphProvider(service)

    def id(self) -> str:
        return "graph"

    def capabilities(self) -> list[WorkerCapability]:
        return [
            WorkerCapability(
                name="graph:expansion",
                description="Wraps Knowledge Graph GraphProvider for optional expansion",
            )
        ]

    def supports(self, plan: QueryExecutionPlan) -> bool:
        return self._provider.should_expand(plan) or "relationship" in (plan.required_indexes or [])

    def depends_on(self) -> list[str]:
        # Prefer index workers first so expansion has candidates when available.
        return ["metadata", "keyword", "entity", "relationship"]

    def execute(self, plan: QueryExecutionPlan, *, context: dict[str, Any] | None = None) -> WorkerEvidence:
        try:
            context = context or {}
            evidence_set = context.get("partial_evidence_set")
            if not isinstance(evidence_set, CandidateEvidenceSet):
                # Build a minimal set from prior worker evidence if provided.
                evidence_set = CandidateEvidenceSet(
                    execution_id="orchestration-partial",
                    plan_id=plan.plan_id,
                    raw_query=plan.raw_query,
                    normalized_query=plan.normalized_query,
                    candidates=list(context.get("partial_candidates") or []),
                )
            graph_evidence = self._provider.expand_candidates(plan, evidence_set)
            items = [item.to_dict() for item in graph_evidence.items]
            return WorkerEvidence(
                worker_id=self.id(),
                success="graph_unavailable" not in graph_evidence.warnings,
                evidence_items=items,
                elapsed_ms=graph_evidence.elapsed_ms,
                error=None if not graph_evidence.warnings else ",".join(graph_evidence.warnings),
                diagnostics={
                    "contribution_score": graph_evidence.contribution_score,
                    "warnings": graph_evidence.warnings,
                    "seed_node_ids": graph_evidence.seed_node_ids,
                },
                source_attribution="graph_provider:knowledge_graph",
            )
        except Exception as exc:  # noqa: BLE001
            return WorkerEvidence(
                worker_id=self.id(),
                success=False,
                error=type(exc).__name__,
                source_attribution="graph_provider:knowledge_graph",
            )

    def health(self) -> WorkerHealth:
        available = self._provider.available
        return WorkerHealth(
            status="healthy" if available else "degraded",
            detail="graph_available" if available else "graph_unavailable",
            checked_at=utc_now_iso(),
        )

    def priority(self) -> int:
        return 90
