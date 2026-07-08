"""Reciprocal rank fusion for hybrid retrieval."""

from __future__ import annotations

from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.hybrid.schemas import DenseSearchHit, FusedCandidate, SparseSearchHit
from app.rag.metadata_retrieval.intent import IntentDetectionResult, QueryIntent


_SPARSE_FAVORING = frozenset({
    QueryIntent.NUMERIC_INTENT,
    QueryIntent.ENTITY_LOOKUP,
    QueryIntent.TABLE_INTENT,
    QueryIntent.LIST_INTENT,
})

_DENSE_FAVORING = frozenset({
    QueryIntent.GENERAL,
    QueryIntent.SECTION_LOOKUP,
})


def resolve_fusion_weights(
    intent: IntentDetectionResult,
    settings: HybridRetrievalSettings,
) -> tuple[float, float]:
    """Return normalized dense/sparse weights based on query intent."""
    dense = settings.dense_weight
    sparse = settings.sparse_weight

    if intent.primary in _SPARSE_FAVORING:
        sparse *= 1.35
        dense *= 0.75
    elif intent.primary in _DENSE_FAVORING:
        dense *= 1.25
        sparse *= 0.85

    total = dense + sparse
    if total <= 0:
        return 0.5, 0.5
    return dense / total, sparse / total


class FusionEngine:
    """Fuse dense and sparse ranked lists using weighted RRF."""

    def fuse(
        self,
        *,
        dense_hits: list[DenseSearchHit],
        sparse_hits: list[SparseSearchHit],
        settings: HybridRetrievalSettings,
        intent: IntentDetectionResult,
    ) -> tuple[list[FusedCandidate], dict[str, float]]:
        dense_weight, sparse_weight = resolve_fusion_weights(intent, settings)
        k = settings.rrf_k

        dense_by_id = {hit.chunk.chunk_id: hit for hit in dense_hits}
        sparse_by_id = {hit.chunk.chunk_id: hit for hit in sparse_hits}
        chunk_ids = list(dict.fromkeys([*dense_by_id.keys(), *sparse_by_id.keys()]))

        fused: list[FusedCandidate] = []
        dense_only = 0
        sparse_only = 0
        both = 0

        for chunk_id in chunk_ids:
            dense_hit = dense_by_id.get(chunk_id)
            sparse_hit = sparse_by_id.get(chunk_id)
            score = 0.0
            explanations: list[str] = []
            sources: list[str] = []

            if dense_hit is not None:
                contribution = dense_weight * (1.0 / (k + dense_hit.rank))
                score += contribution
                sources.append("dense")
                explanations.append(
                    f"dense rank={dense_hit.rank} contribution={contribution:.6f}"
                )
            if sparse_hit is not None:
                contribution = sparse_weight * (1.0 / (k + sparse_hit.rank))
                score += contribution
                sources.append("sparse")
                explanations.append(
                    f"sparse rank={sparse_hit.rank} contribution={contribution:.6f}"
                )

            if dense_hit is not None and sparse_hit is not None:
                both += 1
            elif dense_hit is not None:
                dense_only += 1
            else:
                sparse_only += 1

            chunk = dense_hit.chunk if dense_hit is not None else sparse_hit.chunk
            fused.append(
                FusedCandidate(
                    chunk=chunk,
                    fusion_score=round(score, 6),
                    dense_rank=dense_hit.rank if dense_hit else None,
                    sparse_rank=sparse_hit.rank if sparse_hit else None,
                    raw_cosine_score=dense_hit.raw_cosine_score if dense_hit else 0.0,
                    bm25_score=sparse_hit.bm25_score if sparse_hit else None,
                    source_retrievers=tuple(sources),
                    fusion_explanation=tuple(explanations),
                )
            )

        fused.sort(
            key=lambda item: (
                -item.fusion_score,
                item.dense_rank if item.dense_rank is not None else 9999,
                item.sparse_rank if item.sparse_rank is not None else 9999,
                item.chunk.chunk_id,
            )
        )

        stats = {
            "dense_weight": dense_weight,
            "sparse_weight": sparse_weight,
            "rrf_k": float(k),
            "dense_only": float(dense_only),
            "sparse_only": float(sparse_only),
            "both": float(both),
        }
        return fused, stats
