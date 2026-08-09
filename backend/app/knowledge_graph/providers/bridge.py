"""Compose Execution Engine + GraphProvider without modifying KEE."""

from __future__ import annotations

from app.knowledge_execution.executor.engine import KnowledgeExecutionEngine
from app.knowledge_execution.models.types import CandidateEvidenceSet
from app.knowledge_graph.providers.graph_provider import GraphProvider
from app.query_planner.models.types import QueryExecutionPlan


class GraphAwareExecutionBridge:
    """
    Runs KnowledgeExecutionEngine.execute(plan) then optionally expands via GraphProvider.

    KEE continues to function when the graph is unavailable.
    """

    def __init__(
        self,
        *,
        execution_engine: KnowledgeExecutionEngine | None = None,
        graph_provider: GraphProvider | None = None,
    ) -> None:
        self._engine = execution_engine or KnowledgeExecutionEngine()
        self._graph_provider = graph_provider or GraphProvider()

    def execute(self, plan: QueryExecutionPlan) -> dict:
        evidence_set: CandidateEvidenceSet = self._engine.execute(plan)
        expansion = self._graph_provider.execute_optional(plan, evidence_set)
        return {
            "candidate_evidence_set": evidence_set.to_dict(),
            "graph_expansion": expansion,
        }
