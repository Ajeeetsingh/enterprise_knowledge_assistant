"""Common provider interface for Hybrid Knowledge Index execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.knowledge_execution.models.types import EvidenceItem, ProviderResult
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.query_planner.models.types import QueryExecutionPlan


class IndexProvider(ABC):
    """Execute lookups against a single Hybrid Knowledge Index."""

    name: str

    def __init__(self, manager: KnowledgeIndexManager) -> None:
        self._manager = manager

    @abstractmethod
    def build_queries(self, plan: QueryExecutionPlan) -> list[Any]:
        """Derive lookup queries from the plan without modifying it."""

    def execute(self, plan: QueryExecutionPlan) -> ProviderResult:
        import time

        started = time.perf_counter()
        evidence: list[EvidenceItem] = []
        queries = self.build_queries(plan)
        try:
            for query in queries:
                result = self._manager.lookup(self.name, query)
                for document_id in result.document_ids:
                    knowledge_id = self._resolve_knowledge_id(document_id)
                    evidence.append(
                        EvidenceItem(
                            knowledge_id=knowledge_id,
                            document_id=document_id,
                            source_index=self.name,
                            matched_field=self._matched_field(query),
                            match_type=self._match_type(query),
                            confidence=self._confidence(query, plan),
                            evidence_score=self._score(query, plan),
                            explanation=self._explain(query, document_id, plan),
                            metadata={
                                "query": query,
                                "lookup_elapsed_ms": result.elapsed_ms,
                                "plan_id": plan.plan_id,
                            },
                            relationship_context=self._relationship_context(
                                result.meta, document_id
                            ),
                        )
                    )
            return ProviderResult(
                provider_name=self.name,
                success=True,
                evidence=evidence,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                query_used=queries,
            )
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(
                provider_name=self.name,
                success=False,
                evidence=[],
                elapsed_ms=(time.perf_counter() - started) * 1000,
                error=type(exc).__name__,
                query_used=queries,
            )

    def _resolve_knowledge_id(self, document_id: str) -> str:
        document = self._manager.documents.get(document_id)
        if document is not None:
            return document.knowledge_id
        return document_id

    def _matched_field(self, query: Any) -> str:
        if isinstance(query, dict):
            return str(query.get("field") or query.get("mode") or self.name)
        return self.name

    def _match_type(self, query: Any) -> str:
        if isinstance(query, dict):
            return str(query.get("mode") or "exact")
        return "exact"

    def _confidence(self, query: Any, plan: QueryExecutionPlan) -> float:
        return min(0.95, max(0.4, float(plan.confidence or 0.5)))

    def _score(self, query: Any, plan: QueryExecutionPlan) -> float:
        return round(self._confidence(query, plan) * 1.0, 4)

    def _explain(self, query: Any, document_id: str, plan: QueryExecutionPlan) -> str:
        return f"{self.name} matched document {document_id} for plan {plan.plan_id}"

    def _relationship_context(
        self, meta: dict[str, Any] | None, document_id: str
    ) -> dict[str, Any] | None:
        if not meta:
            return None
        edges = meta.get("edges")
        if not edges:
            return None
        related = [
            edge
            for edge in edges
            if edge.get("source_document_id") == document_id
            or edge.get("target_document_id") == document_id
        ]
        return {"edges": related} if related else {"edges": edges[:5]}
