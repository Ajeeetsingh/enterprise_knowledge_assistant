"""Worker Orchestrator — coordinates eligible workers for a QueryExecutionPlan."""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.knowledge_execution.models.types import CandidateDocument
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_orchestration.merger.evidence_merger import EvidenceMerger
from app.knowledge_orchestration.models.types import (
    OrchestrationDiagnostics,
    OrchestrationResult,
    WorkerEvidence,
    utc_now_iso,
)
from app.knowledge_orchestration.registry.worker_registry import WorkerRegistry
from app.knowledge_orchestration.scheduler.scheduler import WorkerScheduler
from app.knowledge_orchestration.validators.result_validator import OrchestrationValidator
from app.knowledge_orchestration.version import KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION
from app.query_planner.models.types import QueryExecutionPlan


class KnowledgeOrchestrator:
    """
    Plugin-based orchestration over workers wrapping existing providers.

    Not an AI agent framework. Deterministic workers only in this milestone.
    """

    def __init__(
        self,
        *,
        registry: WorkerRegistry | None = None,
        scheduler: WorkerScheduler | None = None,
        merger: EvidenceMerger | None = None,
        index_manager: KnowledgeIndexManager | None = None,
    ) -> None:
        manager = index_manager or KnowledgeIndexManager()
        self._registry = registry or WorkerRegistry.with_defaults(index_manager=manager)
        self._scheduler = scheduler or WorkerScheduler()
        self._merger = merger or EvidenceMerger(manager)
        self._validator = OrchestrationValidator()
        self._runs = 0

    @property
    def registry(self) -> WorkerRegistry:
        return self._registry

    def orchestrate(self, plan: QueryExecutionPlan) -> OrchestrationResult:
        started = time.perf_counter()
        eligible = self._registry.eligible(plan)
        skipped = [
            worker.id()
            for worker in self._registry.list_workers()
            if worker.id() not in {item.id() for item in eligible}
        ]

        def context_factory(prior: list[WorkerEvidence]) -> dict[str, Any]:
            # Build partial candidates from prior successful index workers for graph.
            partial_candidates: list[CandidateDocument] = []
            seen: set[str] = set()
            for evidence in prior:
                if not evidence.success:
                    continue
                for item in evidence.evidence_items:
                    doc_id = str(item.get("document_id") or "")
                    if not doc_id or doc_id in seen or doc_id.startswith("entity:"):
                        continue
                    if item.get("source_index") == "graph":
                        continue
                    seen.add(doc_id)
                    partial_candidates.append(
                        CandidateDocument(
                            document_id=doc_id,
                            knowledge_id=str(item.get("knowledge_id") or doc_id),
                            score=float(item.get("evidence_score") or 0.5),
                            confidence=float(item.get("confidence") or 0.5),
                            supporting_indexes=[str(item.get("source_index") or evidence.worker_id)],
                            explanation="partial orchestration candidate",
                        )
                    )
            return {"partial_candidates": partial_candidates[:20]}

        worker_evidence, schedule, timeline = self._scheduler.run(
            plan,
            eligible,
            context_factory=context_factory,
        )
        evidence_set, merger_report = self._merger.merge(plan, worker_evidence)

        diagnostics = OrchestrationDiagnostics(
            eligible_workers=[worker.id() for worker in eligible],
            skipped_workers=skipped,
            failed_workers=[
                item.worker_id
                for item in worker_evidence
                if not item.success and not item.skipped and not item.timed_out
            ],
            timed_out_workers=[item.worker_id for item in worker_evidence if item.timed_out],
            timeline=timeline,
            schedule=schedule.to_dict(),
            merger=merger_report.to_dict(),
            notes=[
                "Workers wrap existing providers; no duplicated retrieval logic.",
                "Failures continue with partial evidence.",
            ],
        )
        status = "ok"
        if diagnostics.failed_workers or diagnostics.timed_out_workers:
            status = "degraded"
        if not worker_evidence:
            status = "empty"

        result = OrchestrationResult(
            orchestration_id=str(uuid.uuid4()),
            plan_id=plan.plan_id,
            raw_query=plan.raw_query,
            worker_evidence=worker_evidence,
            candidate_evidence_set=evidence_set.to_dict(),
            diagnostics=diagnostics,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 4),
            status=status,
            orchestrator_version=KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION,
            created_at=utc_now_iso(),
        )
        self._validator.validate(result)
        self._runs += 1
        return result

    def statistics(self) -> dict[str, Any]:
        return {
            "runs": self._runs,
            "registered_workers": len(self._registry.list_workers()),
            "worker_metadata": self._registry.metadata(),
            "version": KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION,
        }
