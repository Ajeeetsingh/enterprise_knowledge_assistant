"""Structured query intelligence telemetry."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.logging import get_logger, log_with_fields
from app.rag.query_processing.schemas import QueryProcessingMetrics, QueryProcessingOutcome

if TYPE_CHECKING:
    from app.rag.query_processing.understanding import QueryUnderstanding

logger = get_logger(__name__)


def log_query_processing(
    outcome: QueryProcessingOutcome,
    *,
    metrics: QueryProcessingMetrics,
    understanding: "QueryUnderstanding | None" = None,
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
        expansion_strategy=outcome.expansion_strategy or metrics.expansion_strategy,
        understanding_intent=outcome.understanding_intent,
        understanding_concepts=list(outcome.understanding_concepts),
        understanding_likely_documents=list(outcome.understanding_likely_documents),
    )

    # Temporary acceptance-testing debug block (same channel as ROUTING_DEBUG).
    try:
        from app.query_router.routing_debug import log_query_understanding_stage

        log_query_understanding_stage(
            original_question=outcome.original_query,
            intent=(understanding.intent if understanding else outcome.understanding_intent) or "",
            entities=list(
                understanding.entities if understanding else outcome.detected_entities
            ),
            concepts=list(
                understanding.concepts if understanding else outcome.understanding_concepts
            ),
            likely_documents=list(
                understanding.likely_documents
                if understanding
                else outcome.understanding_likely_documents
            ),
            retrieval_queries=list(outcome.retrieval_queries),
            expansion_strategy=outcome.expansion_strategy or metrics.expansion_strategy or "",
            confidence=float(
                understanding.confidence
                if understanding is not None
                else outcome.confidence_prediction
            ),
            domain=understanding.domain if understanding else "",
            actions=list(understanding.actions) if understanding else [],
        )
    except Exception:  # noqa: BLE001
        pass
