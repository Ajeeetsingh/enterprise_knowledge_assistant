"""Cross-encoder reranking orchestrator."""

from __future__ import annotations

import logging

from app.core.logging import get_logger, log_with_fields
from app.ingestion.retrieval_text import build_retrieval_text, resolve_chunk_heading
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.reranking.config import RerankingSettings
from app.rag.reranking.metrics import log_reranking
from app.rag.reranking.runtime import CrossEncoderRuntime, create_reranker_runtime
from app.rag.reranking.schemas import RerankerMetrics
from app.rag.reranking.scorer import apply_reranker_scores, score_pairs
from app.rag.types import RetrievalResult

logger = get_logger(__name__)


def _rerank_passage(item: RetrievalResult, *, enabled: bool, repetitions: int) -> str:
    """Return reranker input text, weighting the result's known heading.

    Feeds the cross-encoder the same heading-weighted representation used
    for embedding/BM25, so a section's distinguishing heading (e.g. "Who
    are the main issuers?" vs "...investors?") isn't diluted by a longer,
    topically-similar body. ``item.content`` (used for citations/LLM
    context) is untouched.
    """
    if not enabled:
        return item.content
    heading = resolve_chunk_heading(item.section_title, item.hierarchy_path)
    return build_retrieval_text(item.content, heading, repetitions=repetitions)


class CrossEncoderReranker:
    """Production cross-encoder reranker with batch inference and failsafe fallback."""

    def __init__(
        self,
        *,
        settings: RerankingSettings | None = None,
        runtime: CrossEncoderRuntime | None = None,
        metadata_bonus_reference: float | None = None,
    ) -> None:
        self._settings = settings or RerankingSettings.from_settings()
        self._runtime = runtime or create_reranker_runtime(self._settings)
        self._metadata_bonus_reference = (
            metadata_bonus_reference
            if metadata_bonus_reference is not None
            else MetadataRetrievalSettings.from_settings().max_metadata_bonus
        )

    @property
    def settings(self) -> RerankingSettings:
        return self._settings

    @property
    def runtime(self) -> CrossEncoderRuntime:
        return self._runtime

    def preload(self) -> None:
        """Eagerly load the reranker model."""
        self._runtime.preload()

    def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        *,
        top_k: int,
    ) -> list[RetrievalResult]:
        """Rerank metadata-ranked candidates and return the final top-K."""
        if not self._settings.enabled or not candidates:
            return candidates[:top_k]

        pool = candidates[: self._settings.rerank_top_n]
        if len(pool) <= 1:
            if pool:
                pool[0].final_rank = 1
            return pool[:top_k]

        try:
            outcome = score_pairs(
                self._runtime,
                query=query,
                passages=[
                    _rerank_passage(
                        item,
                        enabled=self._settings.heading_weighting_enabled,
                        repetitions=self._settings.heading_weight_repetitions,
                    )
                    for item in pool
                ],
                settings=self._settings,
            )
            reranked = apply_reranker_scores(
                pool,
                outcome.scores,
                metadata_bonus_weight=self._settings.metadata_bonus_weight,
                metadata_bonus_reference=self._metadata_bonus_reference,
            )
            log_reranking(outcome.metrics, query=query)
            return reranked[:top_k]
        except Exception as exc:
            log_with_fields(
                logger,
                logging.WARNING,
                "Cross-encoder reranking failed; falling back to hybrid output",
                query=query,
                model_id=self._runtime.spec.id,
                reason=str(exc),
            )
            fallback_metrics = RerankerMetrics(
                model_id=self._runtime.spec.id,
                model_name=self._runtime.model_name,
                candidates_reranked=len(pool),
                batch_size=self._settings.max_batch_size,
                inference_latency_ms=0.0,
                average_score=0.0,
                top_score=0.0,
                device=self._runtime.device,
                fallback_used=True,
                fallback_reason=str(exc),
            )
            log_reranking(fallback_metrics, query=query)
            return pool[:top_k]
