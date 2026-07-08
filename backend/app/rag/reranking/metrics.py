"""Structured reranking telemetry."""

from __future__ import annotations

import logging

from app.core.logging import get_logger, log_with_fields
from app.rag.reranking.schemas import RerankerMetrics

logger = get_logger(__name__)


def log_reranking(metrics: RerankerMetrics, *, query: str) -> None:
    """Emit structured reranking logs."""
    log_with_fields(
        logger,
        logging.INFO,
        "Cross-encoder reranking completed",
        query=query,
        model_id=metrics.model_id,
        model_name=metrics.model_name,
        candidates_reranked=metrics.candidates_reranked,
        batch_size=metrics.batch_size,
        inference_latency_ms=metrics.inference_latency_ms,
        average_score=metrics.average_score,
        top_score=metrics.top_score,
        device=metrics.device,
        fallback_used=metrics.fallback_used,
        fallback_reason=metrics.fallback_reason,
    )
