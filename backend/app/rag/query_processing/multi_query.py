"""Merge multi-query retrieval results."""

from __future__ import annotations

from dataclasses import replace

from app.rag.types import RetrievalResult

_RRF_K = 60


def merge_multi_query_results(
    result_sets: list[list[RetrievalResult]],
    *,
    limit: int,
) -> list[RetrievalResult]:
    """Fuse ranked lists from multiple retrieval queries by weighted RRF."""
    if not result_sets:
        return []
    if len(result_sets) == 1:
        return result_sets[0][:limit]

    fused_scores: dict[str, float] = {}
    best_result: dict[str, RetrievalResult] = {}

    for results in result_sets:
        for rank, result in enumerate(results, start=1):
            chunk_id = result.chunk_id
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + (
                1.0 / (_RRF_K + rank)
            )
            existing = best_result.get(chunk_id)
            current_score = result.final_score or result.confidence
            if existing is None:
                best_result[chunk_id] = result
            else:
                existing_score = existing.final_score or existing.confidence
                if current_score > existing_score:
                    best_result[chunk_id] = result

    ordered = sorted(
        fused_scores.items(),
        key=lambda item: (-item[1], item[0]),
    )
    merged: list[RetrievalResult] = []
    for rank, (chunk_id, _) in enumerate(ordered[:limit], start=1):
        merged.append(replace(best_result[chunk_id], final_rank=rank))
    return merged
