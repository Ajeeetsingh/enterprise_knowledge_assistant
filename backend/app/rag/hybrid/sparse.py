"""Sparse BM25 retrieval."""

from __future__ import annotations

import time

from app.rag.hybrid.bm25 import BM25Index
from app.rag.hybrid.schemas import SparseSearchHit


class SparseRetriever:
    """Gather BM25 candidates from the sparse index."""

    def gather(
        self,
        bm25_index: BM25Index,
        query: str,
        *,
        limit: int,
        allowed_categories: set[str] | None = None,
        allowed_sources: set[str] | None = None,
    ) -> tuple[list[SparseSearchHit], float]:
        started = time.perf_counter()
        hits = bm25_index.search(
            query,
            limit=limit,
            allowed_categories=allowed_categories,
            allowed_sources=allowed_sources,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return hits, elapsed_ms
