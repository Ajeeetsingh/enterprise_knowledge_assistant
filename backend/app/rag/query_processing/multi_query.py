"""Merge multi-query retrieval results."""

from __future__ import annotations

from dataclasses import replace

from app.rag.passage_quality import should_skip_merge_candidate
from app.rag.types import RetrievalResult

_RRF_K = 60


def merge_multi_query_results(
    result_sets: list[list[RetrievalResult]],
    *,
    limit: int,
) -> list[RetrievalResult]:
    """Fuse ranked lists from multiple retrieval queries.

    Strategy (Phase 3B — diagnostics-backed):
    1. Always reserve the top half of the pool for the **original query**
       (first result set). Expansions previously drowned strong original hits
       (e.g. BPC Document Purpose table at original rank 7 fell out of top-20
       because TOC chunks accumulated RRF across every expansion).
    2. Fill remaining slots with unweighted RRF across all queries, using the
       best per-query ``final_score`` as a tie-breaker.

    Low-information cover/title stubs and short document masthead banners are
    skipped when selecting slots so they cannot displace answer-bearing hits
    (mission/vision regression: cover pages + governance title banners filled
    the reserved half / CE top_k).
    """
    if not result_sets:
        return []
    if len(result_sets) == 1:
        selected_single = [
            item
            for item in result_sets[0]
            if not should_skip_merge_candidate(item.content)
        ][:limit]
        return [
            replace(item, final_rank=rank)
            for rank, item in enumerate(selected_single, start=1)
        ]

    original = result_sets[0]
    reserved_n = min(max(limit // 2, 1), len(original), limit)
    selected: list[RetrievalResult] = []
    seen: set[str] = set()
    for item in original:
        if len(selected) >= reserved_n:
            break
        if should_skip_merge_candidate(item.content):
            continue
        selected.append(item)
        seen.add(item.chunk_id)

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
        key=lambda item: (
            -item[1],
            -(best_result[item[0]].final_score or best_result[item[0]].confidence or 0.0),
            item[0],
        ),
    )
    for chunk_id, _score in ordered:
        if len(selected) >= limit:
            break
        if chunk_id in seen:
            continue
        candidate = best_result[chunk_id]
        if should_skip_merge_candidate(candidate.content):
            continue
        selected.append(candidate)
        seen.add(chunk_id)

    return [
        replace(item, final_rank=rank) for rank, item in enumerate(selected[:limit], start=1)
    ]
