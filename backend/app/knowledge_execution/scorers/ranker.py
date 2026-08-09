"""Deterministic heuristic ranking — no embeddings / LLM / cross-encoder."""

from __future__ import annotations

from app.knowledge_execution.models.types import (
    CandidateDocument,
    EvidenceItem,
    ScoreContribution,
)
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.query_planner.models.types import QueryExecutionPlan


class CandidateRanker:
    def __init__(self, manager: KnowledgeIndexManager | None = None) -> None:
        self._manager = manager

    def rank(
        self,
        *,
        plan: QueryExecutionPlan,
        grouped_evidence: dict[str, list[EvidenceItem]],
    ) -> list[CandidateDocument]:
        candidates: list[CandidateDocument] = []
        for document_id, evidence in grouped_evidence.items():
            knowledge_id = evidence[0].knowledge_id if evidence else document_id
            contributions: list[ScoreContribution] = []
            score = 0.0

            indexes = sorted({item.source_index for item in evidence})
            index_points = min(4.0, float(len(indexes)) * 1.0)
            contributions.append(
                ScoreContribution(
                    factor="supporting_indexes",
                    points=index_points,
                    detail=",".join(indexes),
                )
            )
            score += index_points

            # Evidence volume
            volume_points = min(2.0, 0.25 * len(evidence))
            contributions.append(
                ScoreContribution(factor="evidence_count", points=volume_points, detail=str(len(evidence)))
            )
            score += volume_points

            # Exact metadata / department / collection boosts
            for item in evidence:
                if item.source_index == "metadata" and item.match_type == "exact":
                    contributions.append(
                        ScoreContribution(factor="metadata_exactness", points=1.5, detail=item.matched_field)
                    )
                    score += 1.5
                if item.source_index == "department" and plan.constraints.department:
                    contributions.append(
                        ScoreContribution(factor="department_match", points=1.2, detail=str(item.metadata.get("query")))
                    )
                    score += 1.2
                if item.source_index == "collection" and plan.constraints.collection:
                    contributions.append(
                        ScoreContribution(factor="collection_match", points=1.0, detail=str(item.metadata.get("query")))
                    )
                    score += 1.0
                if item.source_index == "taxonomy":
                    contributions.append(
                        ScoreContribution(factor="taxonomy_specificity", points=1.1, detail=item.match_type)
                    )
                    score += 1.1
                if item.source_index == "entity":
                    contributions.append(
                        ScoreContribution(factor="entity_overlap", points=1.0, detail=str(item.metadata.get("query")))
                    )
                    score += 1.0
                if item.source_index == "relationship":
                    rel_boost = 1.3
                    if item.relationship_context:
                        rel_boost += 0.2
                    contributions.append(
                        ScoreContribution(factor="relationship_strength", points=rel_boost, detail="edge_support")
                    )
                    score += rel_boost
                if item.source_index == "version":
                    version_boost = 1.4 if plan.constraints.latest or plan.filters.get("latest") else 0.8
                    contributions.append(
                        ScoreContribution(factor="version_priority", points=version_boost, detail=item.match_type)
                    )
                    score += version_boost

            # Deduplicate contribution spam by summing per factor
            by_factor: dict[str, ScoreContribution] = {}
            for contrib in contributions:
                existing = by_factor.get(contrib.factor)
                if existing is None:
                    by_factor[contrib.factor] = ScoreContribution(
                        factor=contrib.factor,
                        points=contrib.points,
                        detail=contrib.detail,
                    )
                else:
                    existing.points = round(existing.points + contrib.points, 4)
                    if contrib.detail and contrib.detail not in existing.detail:
                        existing.detail = f"{existing.detail};{contrib.detail}"[:200]
            merged = list(by_factor.values())
            score = round(sum(item.points for item in merged), 4)
            confidence = round(min(0.99, score / 12.0), 4)

            doc_meta = {}
            if self._manager is not None:
                inspected = self._manager.inspect(document_id)
                if inspected:
                    doc_meta = {
                        "filename": (inspected.get("document") or {}).get("filename"),
                        "collections": inspected.get("collection"),
                        "departments": inspected.get("department"),
                        "taxonomy": inspected.get("taxonomy"),
                    }

            explanation = (
                f"Selected via {len(indexes)} index(es): {', '.join(indexes)}. "
                f"Top factors: "
                + ", ".join(
                    f"{c.factor}={c.points}"
                    for c in sorted(merged, key=lambda item: item.points, reverse=True)[:4]
                )
            )
            candidates.append(
                CandidateDocument(
                    document_id=document_id,
                    knowledge_id=knowledge_id,
                    score=score,
                    confidence=confidence,
                    supporting_indexes=indexes,
                    evidence=evidence,
                    score_contributions=merged,
                    explanation=explanation,
                    metadata=doc_meta,
                )
            )

        candidates.sort(key=lambda item: (-item.score, item.document_id))
        for index, candidate in enumerate(candidates, start=1):
            candidate.rank = index
        return candidates
