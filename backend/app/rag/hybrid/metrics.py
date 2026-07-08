"""Hybrid retrieval metrics helpers."""

from __future__ import annotations

import logging

from app.core.logging import get_logger, log_with_fields
from app.rag.hybrid.schemas import HybridRetrievalMetrics

logger = get_logger(__name__)


def log_hybrid_retrieval(
    *,
    query: str,
    metrics: HybridRetrievalMetrics,
    top_fusion_scores: list[float],
) -> None:
    """Emit structured hybrid retrieval telemetry."""
    log_with_fields(
        logger,
        logging.INFO,
        "Hybrid retrieval completed",
        query=query,
        dense_latency_ms=metrics.dense_latency_ms,
        sparse_latency_ms=metrics.sparse_latency_ms,
        fusion_latency_ms=metrics.fusion_latency_ms,
        metadata_latency_ms=metrics.metadata_latency_ms,
        total_latency_ms=metrics.total_latency_ms,
        dense_candidate_count=metrics.dense_candidate_count,
        sparse_candidate_count=metrics.sparse_candidate_count,
        fused_candidate_count=metrics.fused_candidate_count,
        dense_only_count=metrics.dense_only_count,
        sparse_only_count=metrics.sparse_only_count,
        both_count=metrics.both_count,
        fusion_statistics=metrics.fusion_statistics,
        top_fusion_scores=top_fusion_scores,
    )
