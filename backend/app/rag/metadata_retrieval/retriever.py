"""Metadata-aware retrieval orchestrator."""

from __future__ import annotations

import logging
import time

from typing import TYPE_CHECKING

from app.core.logging import get_logger, log_with_fields
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.metadata_retrieval.intent import detect_query_intent
from app.rag.metadata_retrieval.scorer import score_candidate
from app.ingestion.vector_store.candidates import VectorSearchCandidate
from app.rag.metadata_retrieval.types import MetadataScoreBreakdown
from app.rag.metadata_fields import metadata_fields_from_chunk
from app.rag.retriever import SemanticRetriever
from app.rag.types import RetrievalResult, calibrate_confidence

if TYPE_CHECKING:
    from app.ingestion.vector_store.faiss_store import FaissVectorStore

logger = get_logger(__name__)


class MetadataAwareRetriever:
    """Rescore FAISS candidates using deterministic metadata signals."""

    def __init__(self, settings: MetadataRetrievalSettings | None = None) -> None:
        self._settings = settings or MetadataRetrievalSettings.from_settings()

    @property
    def settings(self) -> MetadataRetrievalSettings:
        return self._settings

    def search_vector_store(
        self,
        vector_store: FaissVectorStore,
        query: str,
        *,
        top_k: int,
        allowed_categories: set[str] | None = None,
        allowed_sources: set[str] | None = None,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        if not self._settings.enabled:
            return vector_store.search(
                query,
                top_k=top_k,
                allowed_categories=allowed_categories,
                allowed_sources=allowed_sources,
                min_score=min_score,
            )

        search_k = min(
            vector_store.size,
            max(top_k * self._settings.candidate_multiplier, top_k),
        )
        candidates = vector_store.gather_candidates(
            query,
            limit=search_k,
            allowed_categories=allowed_categories,
            allowed_sources=allowed_sources,
            min_score=min_score,
        )
        return self._rescore_and_rank(query, candidates, top_k=top_k)

    def search_semantic_retriever(
        self,
        retriever: SemanticRetriever,
        query: str,
        *,
        top_k: int,
        allowed_categories: set[str] | None = None,
        allowed_sources: set[str] | None = None,
    ) -> list[RetrievalResult]:
        if not self._settings.enabled:
            return retriever.search(
                query,
                top_k=top_k,
                allowed_categories=allowed_categories,
                allowed_sources=allowed_sources,
            )

        search_k = min(
            len(retriever.chunks),
            max(top_k * self._settings.candidate_multiplier, top_k),
        )
        candidates = retriever.gather_candidates(
            query,
            limit=search_k,
            allowed_categories=allowed_categories,
            allowed_sources=allowed_sources,
        )
        return self._rescore_and_rank(query, candidates, top_k=top_k)

    def rescore_candidates(
        self,
        query: str,
        candidates: list[VectorSearchCandidate],
        *,
        top_k: int,
    ) -> list[RetrievalResult]:
        """Rescore pre-fused hybrid candidates and return ranked results."""
        return self._rescore_and_rank(query, candidates, top_k=top_k)

    def _rescore_and_rank(
        self,
        query: str,
        candidates: list[VectorSearchCandidate],
        *,
        top_k: int,
    ) -> list[RetrievalResult]:
        started = time.perf_counter()
        if not candidates:
            return []

        intent_result = detect_query_intent(query)
        scored: list[tuple[VectorSearchCandidate, MetadataScoreBreakdown]] = []

        for candidate in candidates:
            base_score = candidate.raw_cosine_score
            if base_score <= 0 and candidate.bm25_score is not None:
                base_score = min(0.75, candidate.bm25_score / 10.0)
            calibrated = calibrate_confidence(base_score)
            breakdown = score_candidate(
                query,
                candidate,
                intent_result=intent_result,
                settings=self._settings,
                peers=candidates,
                calibrated_cosine=calibrated,
            )
            scored.append((candidate, breakdown))

        scored.sort(
            key=lambda item: (
                -item[1].final_score,
                -(item[0].fusion_score or 0.0),
                -item[1].raw_cosine_score,
                _reading_order(item[0]),
                item[0].chunk.chunk_id,
            )
        )

        results: list[RetrievalResult] = []
        for candidate, breakdown in scored[:top_k]:
            chunk = candidate.chunk
            metadata_fields = metadata_fields_from_chunk(chunk)
            metadata_fields.pop("chunk_type", None)
            results.append(
                RetrievalResult(
                    content=chunk.content,
                    source=chunk.source,
                    category=chunk.category,
                    confidence=breakdown.final_score,
                    chunk_id=chunk.chunk_id,
                    **metadata_fields,
                    raw_cosine_score=breakdown.raw_cosine_score,
                    metadata_bonus=breakdown.metadata_bonus,
                    final_score=breakdown.final_score,
                    score_explanation=breakdown.explanations,
                    detected_intent=breakdown.detected_intent,
                    chunk_type=breakdown.chunk_type,
                    dense_rank=candidate.dense_rank,
                    sparse_rank=candidate.sparse_rank,
                    fusion_score=candidate.fusion_score,
                    fusion_explanation=candidate.fusion_explanation,
                    source_retrievers=candidate.source_retrievers,
                )
            )

        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        log_with_fields(
            logger,
            logging.INFO,
            "Metadata-aware retrieval rescoring completed",
            query=query,
            detected_intent=intent_result.primary.value,
            intent_signals=list(intent_result.signals),
            candidate_count=len(candidates),
            returned_count=len(results),
            rescoring_latency_ms=elapsed_ms,
            top_raw_scores=[result.raw_cosine_score for result in results],
            top_metadata_bonuses=[result.metadata_bonus for result in results],
            top_final_scores=[result.final_score for result in results],
            top_chunk_types=[result.chunk_type for result in results],
            applied_boosts=[
                {
                    "chunk_id": result.chunk_id,
                    "explanations": result.score_explanation,
                }
                for result in results
            ],
        )
        return results


def _reading_order(candidate: VectorSearchCandidate) -> int:
    metadata = candidate.chunk.metadata
    if metadata is not None and hasattr(metadata, "reading_order"):
        return int(metadata.reading_order)
    return 0
