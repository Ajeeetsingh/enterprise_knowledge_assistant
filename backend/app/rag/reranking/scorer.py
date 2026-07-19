"""Batch cross-encoder scoring."""

from __future__ import annotations

import math
import time
from dataclasses import replace

from app.rag.reranking.config import RerankingSettings
from app.rag.reranking.runtime import CrossEncoderRuntime
from app.rag.reranking.schemas import RerankOutcome, RerankerMetrics
from app.rag.types import calibrate_confidence


def _normalize_scores(scores: list[float]) -> list[float]:
    """Min-max normalize raw cross-encoder logits to [0, 1] within one pool.

    Used to blend the cross-encoder's opinion with the metadata bonus on a
    comparable scale — the model's own scores are unit-less logits, so a
    fixed-scale bonus cannot be combined with them directly.
    """
    if not scores:
        return []
    low = min(scores)
    high = max(scores)
    if high <= low:
        return [1.0 for _ in scores]
    return [round((score - low) / (high - low), 4) for score in scores]


def _metadata_component(metadata_bonus: float | None, reference: float) -> float:
    """Scale a metadata bonus to [0, 1] relative to its configured maximum."""
    if not metadata_bonus or reference <= 0:
        return 0.0
    return min(1.0, max(0.0, metadata_bonus / reference))


def _reranker_display_confidence(result, raw_reranker_score: float) -> float:
    """Map reranker logits to an absolute confidence without per-query min-max inflation."""
    if result.raw_cosine_score is not None:
        return calibrate_confidence(result.raw_cosine_score)
    sigmoid = 1.0 / (1.0 + math.exp(-raw_reranker_score))
    return round(sigmoid, 4)


def score_pairs(
    runtime: CrossEncoderRuntime,
    *,
    query: str,
    passages: list[str],
    settings: RerankingSettings,
) -> RerankOutcome:
    """Score query-passage pairs in batches."""
    if not passages:
        metrics = RerankerMetrics(
            model_id=runtime.spec.id,
            model_name=runtime.model_name,
            candidates_reranked=0,
            batch_size=settings.max_batch_size,
            inference_latency_ms=0.0,
            average_score=0.0,
            top_score=0.0,
            device=runtime.device,
        )
        return RerankOutcome(scores=[], metrics=metrics)

    model = runtime.get_model()
    pairs = [[query, passage] for passage in passages]
    started = time.perf_counter()
    raw_scores = model.predict(
        pairs,
        batch_size=settings.max_batch_size,
        show_progress_bar=False,
    )
    inference_latency_ms = round((time.perf_counter() - started) * 1000, 3)
    scores = [float(value) for value in raw_scores]
    metrics = RerankerMetrics(
        model_id=runtime.spec.id,
        model_name=runtime.model_name,
        candidates_reranked=len(passages),
        batch_size=settings.max_batch_size,
        inference_latency_ms=inference_latency_ms,
        average_score=round(sum(scores) / len(scores), 4),
        top_score=round(max(scores), 4),
        device=runtime.device,
    )
    return RerankOutcome(scores=scores, metrics=metrics)


def _build_rerank_explanation(
    result,
    *,
    reranker_score: float,
    final_rank: int,
) -> list[str]:
    """Append reranker explainability lines to existing hybrid/metadata context."""
    lines: list[str] = []
    if result.dense_rank is not None:
        lines.append(f"Dense Rank      {result.dense_rank}")
    if result.sparse_rank is not None:
        lines.append(f"Sparse Rank     {result.sparse_rank}")
    if result.fusion_score is not None:
        lines.append(f"Fusion Score    {result.fusion_score:.3f}")
    if result.metadata_bonus is not None:
        sign = "+" if result.metadata_bonus >= 0 else ""
        lines.append(f"Metadata Bonus  {sign}{result.metadata_bonus:.2f}")
    lines.append(f"Reranker Score  {reranker_score:.3f}")
    lines.append(f"Final Rank      {final_rank}")
    if result.score_explanation:
        return list(result.score_explanation) + lines
    return lines


def apply_reranker_scores(
    results: list,
    scores: list[float],
    *,
    metadata_bonus_weight: float = 0.0,
    metadata_bonus_reference: float = 1.0,
) -> list:
    """Return results sorted by (metadata-aware) reranker score.

    When ``metadata_bonus_weight`` is 0 (the default), ranking is purely the
    raw cross-encoder score — identical to the original behaviour. When
    positive, the final ranking blends the normalized cross-encoder score
    with each result's existing ``metadata_bonus`` (heading/section
    similarity, chunk-type intent, continuity — computed upstream by
    ``MetadataAwareRetriever`` and already present on the result). This is
    "metadata-aware reranking": the cross-encoder model itself is untouched,
    only how its output is combined with signals the retriever already
    computed changes.
    """
    if not results or not scores:
        return results

    normalized_scores = _normalize_scores(scores)
    enriched: list = []
    for result, reranker_score, normalized_score in zip(
        results, scores, normalized_scores, strict=True
    ):
        display_confidence = _reranker_display_confidence(result, reranker_score)
        combined_score = reranker_score
        if metadata_bonus_weight > 0:
            metadata_component = _metadata_component(
                result.metadata_bonus, metadata_bonus_reference
            )
            combined_score = (
                (1 - metadata_bonus_weight) * normalized_score
                + metadata_bonus_weight * metadata_component
            )
        enriched.append(
            replace(
                result,
                reranker_score=round(reranker_score, 4),
                confidence=display_confidence,
                final_score=round(combined_score, 4),
            )
        )

    enriched.sort(
        key=lambda item: (
            -(item.final_score if item.final_score is not None else 0.0),
            item.chunk_id,
        )
    )
    ranked: list = []
    for rank, item in enumerate(enriched, start=1):
        ranked.append(
            replace(
                item,
                final_rank=rank,
                score_explanation=_build_rerank_explanation(
                    item,
                    reranker_score=item.reranker_score or 0.0,
                    final_rank=rank,
                ),
            )
        )
    return ranked
