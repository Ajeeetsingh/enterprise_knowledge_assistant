"""Optional GraphProvider for Execution Engine integration.

Lives outside the Knowledge Execution Engine package so KEE remains unmodified.
When a QueryExecutionPlan requests graph expansion (Graph Ready / relationship
requirements), this provider expands candidate knowledge nodes and returns
GraphEvidence. If the graph is unavailable, it fails soft and returns empty evidence.
"""

from __future__ import annotations

import time
from typing import Any

from app.knowledge_execution.models.types import CandidateEvidenceSet
from app.knowledge_graph.models.types import GraphEvidence
from app.knowledge_graph.services.graph_service import KnowledgeGraphService
from app.query_planner.models.types import QueryExecutionPlan


class GraphProvider:
    """Provider interface used by the shadow execution bridge."""

    name = "knowledge_graph"

    def __init__(self, graph_service: KnowledgeGraphService | None = None) -> None:
        self._service = graph_service or KnowledgeGraphService()

    @property
    def available(self) -> bool:
        return self._service.available

    def should_expand(self, plan: QueryExecutionPlan) -> bool:
        if plan.preferred_strategy == "Graph Ready":
            return True
        if plan.relationship_requirements:
            return True
        if any(intent.intent == "RELATIONSHIP_QUERY" for intent in plan.intents):
            return True
        return False

    def expand_candidates(
        self,
        plan: QueryExecutionPlan,
        evidence_set: CandidateEvidenceSet,
        *,
        max_depth: int = 2,
    ) -> GraphEvidence:
        """Expand graph around execution candidates. Never raises into callers."""
        started = time.perf_counter()
        if not self.available:
            return GraphEvidence(
                warnings=["graph_unavailable"],
                elapsed_ms=(time.perf_counter() - started) * 1000,
            )
        if not self.should_expand(plan) and not evidence_set.candidates:
            return GraphEvidence(
                warnings=["graph_expansion_not_requested"],
                elapsed_ms=(time.perf_counter() - started) * 1000,
            )
        try:
            seeds = []
            for candidate in evidence_set.candidates[:10]:
                seeds.append(self._service.knowledge_object_node_id(candidate.knowledge_id))
            if not seeds and plan.entities:
                # Fall back to entity nodes when no candidates yet
                for entity in plan.entities[:5]:
                    seeds.append(f"entity:{entity.text.lower()}")
            mode = "relationship"
            if plan.constraints.department:
                mode = "department"
            if plan.constraints.latest or plan.constraints.version_label:
                mode = "version"
            if plan.constraints.taxonomy_path:
                mode = "taxonomy"
            # Expand from first seed then merge remaining via service expander API.
            if not seeds:
                return GraphEvidence(
                    warnings=["no_seeds"],
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                )
            evidence = self._service.expand_node(
                seeds[0],
                mode=mode,
                max_depth=max_depth,
            )
            if len(seeds) > 1:
                extra_items = list(evidence.items)
                for seed in seeds[1:]:
                    more = self._service.expand_node(seed, mode=mode, max_depth=max_depth)
                    extra_items.extend(more.items)
                    evidence.warnings.extend(more.warnings)
                # Deduplicate by node_id
                best = {}
                for item in extra_items:
                    existing = best.get(item.node_id)
                    if existing is None or item.score > existing.score:
                        best[item.node_id] = item
                evidence.items = sorted(best.values(), key=lambda item: (-item.score, item.node_id))
                evidence.seed_node_ids = seeds
                evidence.contribution_score = round(
                    sum(item.score for item in evidence.items) / max(1, len(evidence.items)),
                    4,
                )
            return evidence
        except Exception as exc:  # noqa: BLE001
            return GraphEvidence(
                warnings=[f"graph_expansion_failed:{type(exc).__name__}"],
                elapsed_ms=(time.perf_counter() - started) * 1000,
            )

    def execute_optional(
        self,
        plan: QueryExecutionPlan,
        evidence_set: CandidateEvidenceSet,
    ) -> dict[str, Any]:
        """Return a structured expansion payload for Shadow diagnostics."""
        evidence = self.expand_candidates(plan, evidence_set)
        return {
            "provider": self.name,
            "available": self.available,
            "requested": self.should_expand(plan),
            "graph_evidence": evidence.to_dict(),
        }
