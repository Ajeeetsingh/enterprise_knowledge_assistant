"""Dense retrieval via production FAISS."""

from __future__ import annotations

import time

from app.ingestion.vector_store.faiss_store import FaissVectorStore
from app.rag.hybrid.schemas import DenseSearchHit


class DenseRetriever:
    """Gather dense vector candidates without duplicating FAISS logic."""

    def gather(
        self,
        vector_store: FaissVectorStore,
        query: str,
        *,
        limit: int,
        allowed_categories: set[str] | None = None,
        allowed_sources: set[str] | None = None,
        min_score: float = 0.0,
    ) -> tuple[list[DenseSearchHit], float]:
        started = time.perf_counter()
        candidates = vector_store.gather_candidates(
            query,
            limit=limit,
            allowed_categories=allowed_categories,
            allowed_sources=allowed_sources,
            min_score=min_score,
        )
        hits = [
            DenseSearchHit(
                chunk=candidate.chunk,
                raw_cosine_score=candidate.raw_cosine_score,
                rank=rank,
            )
            for rank, candidate in enumerate(candidates, start=1)
        ]
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return hits, elapsed_ms
