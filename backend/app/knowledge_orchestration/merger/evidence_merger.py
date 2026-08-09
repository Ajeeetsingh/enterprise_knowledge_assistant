"""Merge WorkerEvidence into CandidateEvidenceSet."""

from __future__ import annotations

import uuid

from app.knowledge_execution.aggregators.evidence import EvidenceAggregator
from app.knowledge_execution.models.types import (
    CandidateEvidenceSet,
    EvidenceItem,
    ExecutionDiagnostics,
    ExecutionStatistics,
    utc_now_iso as kee_utc_now,
)
from app.knowledge_execution.scorers.ranker import CandidateRanker
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_orchestration.models.types import MergerReport, WorkerEvidence
from app.knowledge_orchestration.version import KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION
from app.query_planner.models.types import QueryExecutionPlan


class EvidenceMerger:
    """
    Merge worker outputs into CandidateEvidenceSet.

    Reuses KEE EvidenceAggregator + CandidateRanker (no duplicated ranking logic).
    """

    def __init__(self, index_manager: KnowledgeIndexManager | None = None) -> None:
        self._manager = index_manager or KnowledgeIndexManager()
        self._aggregator = EvidenceAggregator()
        self._ranker = CandidateRanker(self._manager)

    def merge(
        self,
        plan: QueryExecutionPlan,
        worker_evidence: list[WorkerEvidence],
    ) -> tuple[CandidateEvidenceSet, MergerReport]:
        raw_items: list[EvidenceItem] = []
        sources: dict[str, int] = {}
        for result in worker_evidence:
            if result.skipped or result.timed_out or not result.success:
                continue
            sources[result.worker_id] = sources.get(result.worker_id, 0) + len(result.evidence_items)
            for payload in result.evidence_items:
                # Graph evidence items are node-shaped; map into EvidenceItem when possible.
                if "document_id" in payload and "source_index" in payload:
                    raw_items.append(
                        EvidenceItem(
                            knowledge_id=str(payload.get("knowledge_id") or ""),
                            document_id=str(payload.get("document_id") or ""),
                            source_index=str(payload.get("source_index") or result.worker_id),
                            matched_field=str(payload.get("matched_field") or result.worker_id),
                            match_type=str(payload.get("match_type") or "worker"),
                            confidence=float(payload.get("confidence") or 0.5),
                            evidence_score=float(
                                payload.get("evidence_score") or payload.get("score") or 0.5
                            ),
                            explanation=str(
                                payload.get("explanation") or f"from worker {result.worker_id}"
                            ),
                            metadata={
                                **dict(payload.get("metadata") or {}),
                                "worker_id": result.worker_id,
                                "source_attribution": result.source_attribution,
                            },
                            relationship_context=payload.get("relationship_context"),
                        )
                    )
                elif "node_id" in payload:
                    # Graph node evidence — attribute without inventing documents.
                    node_id = str(payload.get("node_id"))
                    raw_items.append(
                        EvidenceItem(
                            knowledge_id=node_id.replace("ko:", "") if node_id.startswith("ko:") else node_id,
                            document_id=node_id,
                            source_index="graph",
                            matched_field=str(payload.get("edge_type") or "graph"),
                            match_type="graph_expansion",
                            confidence=float(payload.get("confidence") or 0.5),
                            evidence_score=float(payload.get("score") or 0.5),
                            explanation=str(payload.get("explanation") or "graph expansion"),
                            metadata={
                                **dict(payload.get("metadata") or {}),
                                "worker_id": result.worker_id,
                                "node_type": payload.get("node_type"),
                                "label": payload.get("label"),
                                "source_attribution": result.source_attribution,
                            },
                        )
                    )

        input_count = len(raw_items)
        # Fake ProviderResult-like aggregation via temporary grouping
        from app.knowledge_execution.models.types import ProviderResult

        provider_result = ProviderResult(
            provider_name="orchestration_merger",
            success=True,
            evidence=raw_items,
        )
        grouped = self._aggregator.aggregate([provider_result])
        flattened = self._aggregator.flatten(grouped)
        duplicates_removed = max(0, input_count - len(flattened))

        # Normalize scores
        if flattened:
            max_score = max(item.evidence_score for item in flattened) or 1.0
            for item in flattened:
                item.evidence_score = round(item.evidence_score / max_score, 4)

        # Rebuild grouped after normalization
        grouped = {}
        for item in flattened:
            grouped.setdefault(item.document_id, []).append(item)

        candidates = self._ranker.rank(plan=plan, grouped_evidence=grouped)
        conflicts_resolved = 0
        # Conflict resolution: same document from multiple workers — ranker already merges.
        for candidate in candidates:
            worker_ids = {
                str((item.metadata or {}).get("worker_id"))
                for item in candidate.evidence
                if (item.metadata or {}).get("worker_id")
            }
            if len(worker_ids) > 1:
                conflicts_resolved += 1
                candidate.metadata["worker_sources"] = sorted(worker_ids)

        evidence_set = CandidateEvidenceSet(
            execution_id=str(uuid.uuid4()),
            plan_id=plan.plan_id,
            raw_query=plan.raw_query,
            normalized_query=plan.normalized_query,
            candidates=candidates,
            ranking=[candidate.document_id for candidate in candidates],
            confidence=(
                round(sum(c.confidence for c in candidates) / len(candidates), 4)
                if candidates
                else 0.0
            ),
            statistics=ExecutionStatistics(
                providers_executed=sum(1 for item in worker_evidence if not item.skipped),
                evidence_collected=len(flattened),
                candidates_generated=len(candidates),
                average_candidate_score=(
                    round(sum(c.score for c in candidates) / len(candidates), 4)
                    if candidates
                    else 0.0
                ),
                failures=sum(1 for item in worker_evidence if not item.success and not item.skipped),
                parallel=True,
            ),
            diagnostics=ExecutionDiagnostics(
                providers_selected=[item.worker_id for item in worker_evidence],
                providers_succeeded=[item.worker_id for item in worker_evidence if item.success],
                providers_failed=[
                    item.worker_id
                    for item in worker_evidence
                    if not item.success and not item.skipped
                ],
                notes=[f"merged_by={KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION}"],
            ),
            engine_version=KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION,
            created_at=kee_utc_now(),
            status="ok",
        )
        report = MergerReport(
            input_evidence_count=input_count,
            output_evidence_count=len(flattened),
            duplicates_removed=duplicates_removed,
            conflicts_resolved=conflicts_resolved,
            sources=sources,
            notes=["score_normalized", "source_attribution_preserved"],
        )
        return evidence_set, report
