"""Structured query intelligence telemetry."""

from __future__ import annotations

import logging

from app.core.logging import get_logger, log_with_fields
from app.rag.query_processing.schemas import QueryProcessingMetrics, QueryProcessingOutcome

logger = get_logger(__name__)


def log_query_processing(
    outcome: QueryProcessingOutcome,
    *,
    metrics: QueryProcessingMetrics,
) -> None:
    """Emit structured query processing logs."""
    log_with_fields(
        logger,
        logging.INFO,
        "Query intelligence processing completed",
        original_query=outcome.original_query,
        classification=metrics.classification,
        expansion_rules_applied=list(metrics.expansion_rules_applied),
        generated_query_count=metrics.generated_query_count,
        retrieval_strategy=metrics.retrieval_strategy,
        processing_latency_ms=metrics.processing_latency_ms,
        detected_entities=list(outcome.detected_entities),
        retrieval_queries=list(outcome.retrieval_queries),
        strategy_sparse_weight=outcome.strategy.sparse_weight,
        strategy_dense_weight=outcome.strategy.dense_weight,
        confidence_prediction=outcome.confidence_prediction,
        fallback_used=metrics.fallback_used,
        fallback_reason=metrics.fallback_reason,
    )
