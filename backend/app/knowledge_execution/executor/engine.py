"""Knowledge Execution Engine — orchestrates plan execution over Hybrid Indexes."""

from __future__ import annotations

import time
import uuid

from app.knowledge_execution.aggregators.evidence import EvidenceAggregator
from app.knowledge_execution.diagnostics.builder import DiagnosticsBuilder
from app.knowledge_execution.dispatcher.dispatcher import ExecutionDispatcher
from app.knowledge_execution.metrics.provider_metrics import MetricsRegistry
from app.knowledge_execution.models.types import (
    CandidateEvidenceSet,
    EvidenceGraphEdge,
    ExecutionStatistics,
    utc_now_iso,
)
from app.knowledge_execution.providers.catalog import build_providers
from app.knowledge_execution.scorers.ranker import CandidateRanker
from app.knowledge_execution.validators.evidence_set import EvidenceSetValidator
from app.knowledge_execution.version import KNOWLEDGE_EXECUTION_PIPELINE_VERSION
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.query_planner.models.types import QueryExecutionPlan


class KnowledgeExecutionEngine:
    """
    Consume a QueryExecutionPlan and produce a CandidateEvidenceSet.

    Never calls FAISS, BM25, reranker, or LLM.
    Never modifies the input plan.
    """

    def __init__(
        self,
        *,
        index_manager: KnowledgeIndexManager | None = None,
        max_workers: int = 8,
    ) -> None:
        self._manager = index_manager or KnowledgeIndexManager()
        self._providers = build_providers(self._manager)
        self._dispatcher = ExecutionDispatcher(self._providers, max_workers=max_workers)
        self._aggregator = EvidenceAggregator()
        self._ranker = CandidateRanker(self._manager)
        self._diagnostics = DiagnosticsBuilder()
        self._validator = EvidenceSetValidator()
        self._metrics = MetricsRegistry()
        self._executions = 0

    @property
    def version(self) -> str:
        return KNOWLEDGE_EXECUTION_PIPELINE_VERSION

    @property
    def metrics(self) -> MetricsRegistry:
        return self._metrics

    def execute(self, plan: QueryExecutionPlan) -> CandidateEvidenceSet:
        started = time.perf_counter()
        selected = self._dispatcher.select(plan)
        provider_results = self._dispatcher.execute_parallel(plan)
        self._metrics.record(provider_results)

        grouped = self._aggregator.aggregate(provider_results)
        candidates = self._ranker.rank(plan=plan, grouped_evidence=grouped)
        diagnostics = self._diagnostics.build(selected=selected, provider_results=provider_results)

        edges: list[EvidenceGraphEdge] = []
        for result in provider_results:
            if result.provider_name != "relationship" or not result.success:
                continue
            for item in result.evidence:
                for edge in (item.relationship_context or {}).get("edges") or []:
                    edges.append(
                        EvidenceGraphEdge(
                            source_document_id=str(edge.get("source_document_id") or ""),
                            target_document_id=str(edge.get("target_document_id") or ""),
                            relationship_type=str(edge.get("relationship_type") or ""),
                            confidence=float(edge.get("confidence") or 0.0),
                        )
                    )

        latency = (time.perf_counter() - started) * 1000
        avg_score = (
            sum(candidate.score for candidate in candidates) / len(candidates) if candidates else 0.0
        )
        failures = sum(1 for item in provider_results if not item.success)
        evidence_count = sum(len(items) for items in grouped.values())
        overall_confidence = (
            sum(candidate.confidence for candidate in candidates) / len(candidates)
            if candidates
            else 0.0
        )

        evidence_set = CandidateEvidenceSet(
            execution_id=str(uuid.uuid4()),
            plan_id=plan.plan_id,
            raw_query=plan.raw_query,
            normalized_query=plan.normalized_query,
            candidates=candidates,
            evidence_graph=edges[:200],
            provider_results=provider_results,
            statistics=ExecutionStatistics(
                execution_latency_ms=round(latency, 4),
                providers_executed=len(provider_results),
                evidence_collected=evidence_count,
                candidates_generated=len(candidates),
                average_candidate_score=round(avg_score, 4),
                failures=failures,
                parallel=len(selected) > 1,
            ),
            diagnostics=diagnostics,
            ranking=[candidate.document_id for candidate in candidates],
            confidence=round(overall_confidence, 4),
            engine_version=self.version,
            created_at=utc_now_iso(),
            status="ok" if failures == 0 else "degraded",
        )
        self._validator.validate(evidence_set)
        self._executions += 1
        return evidence_set

    def statistics(self) -> dict:
        return {
            "executions": self._executions,
            "provider_metrics": self._metrics.snapshot(),
            "engine_version": self.version,
        }
