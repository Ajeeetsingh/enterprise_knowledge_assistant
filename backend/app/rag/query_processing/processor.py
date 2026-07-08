"""Query intelligence orchestrator."""

from __future__ import annotations

import time

from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.query_processing.classifier import classify_query
from app.rag.query_processing.config import QueryProcessingSettings
from app.rag.query_processing.expander import expand_query, generate_retrieval_queries
from app.rag.query_processing.metrics import log_query_processing
from app.rag.query_processing.registry import QueryRulesRegistry, StrategySpec, get_rules
from app.rag.query_processing.schemas import (
    QueryProcessingMetrics,
    QueryProcessingOutcome,
    RetrievalStrategy,
)
from app.rag.query_processing.strategy import select_strategy
from app.rag.reranking.config import RerankingSettings


def _predict_confidence(
    classification_confidence: float,
    *,
    query_count: int,
    rules_applied: int,
) -> float:
    boost = min(0.15, rules_applied * 0.02)
    multi_query_boost = 0.05 if query_count > 1 else 0.0
    return round(min(0.95, classification_confidence + boost + multi_query_boost), 4)


class QueryProcessor:
    """Production query intelligence engine with graceful fallback."""

    def __init__(
        self,
        *,
        settings: QueryProcessingSettings | None = None,
        hybrid_settings: HybridRetrievalSettings | None = None,
        metadata_settings: MetadataRetrievalSettings | None = None,
        reranking_settings: RerankingSettings | None = None,
    ) -> None:
        self._settings = settings or QueryProcessingSettings.from_settings()
        self._hybrid_settings = hybrid_settings or HybridRetrievalSettings.from_settings()
        self._metadata_settings = metadata_settings or MetadataRetrievalSettings.from_settings()
        self._reranking_settings = reranking_settings or RerankingSettings.from_settings()
        self._registry = get_rules(self._settings.registry_path)

    @property
    def settings(self) -> QueryProcessingSettings:
        return self._settings

    def _default_strategy(self) -> RetrievalStrategy:
        spec = self._registry.strategies.get("general", StrategySpec(name="general"))
        return RetrievalStrategy(
            name=spec.name,
            sparse_weight=round(
                self._hybrid_settings.sparse_weight * spec.sparse_weight_multiplier,
                4,
            ),
            dense_weight=round(
                self._hybrid_settings.dense_weight * spec.dense_weight_multiplier,
                4,
            ),
            metadata_bonus_multiplier=spec.metadata_bonus_multiplier,
            rerank_top_n=spec.rerank_top_n or self._reranking_settings.rerank_top_n,
            retrieval_depth_multiplier=spec.retrieval_depth_multiplier,
            explanation=("default_strategy",),
        )

    def process(self, query: str) -> QueryProcessingOutcome:
        """Process a user query before retrieval."""
        started = time.perf_counter()
        default_strategy = self._default_strategy()

        if not self._settings.enabled:
            return QueryProcessingOutcome.passthrough(query, strategy=default_strategy)

        try:
            classification = classify_query(query)
            normalized, expanded, detected_entities, rules_applied = expand_query(
                query,
                registry=self._registry,
                settings=self._settings,
            )
            strategy = select_strategy(
                classification,
                registry=self._registry,
                hybrid_settings=self._hybrid_settings,
                metadata_settings=self._metadata_settings,
                reranking_settings=self._reranking_settings,
                settings=self._settings,
            )
            retrieval_queries = generate_retrieval_queries(
                original_query=query,
                normalized_query=normalized,
                expanded_query=expanded,
                classification=classification,
                detected_entities=detected_entities,
                registry=self._registry,
                settings=self._settings,
            )
            confidence = _predict_confidence(
                classification.confidence,
                query_count=len(retrieval_queries),
                rules_applied=len(rules_applied),
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            metrics = QueryProcessingMetrics(
                classification=classification.category.value,
                expansion_rules_applied=rules_applied,
                generated_query_count=len(retrieval_queries),
                retrieval_strategy=strategy.name,
                processing_latency_ms=latency_ms,
            )
            outcome = QueryProcessingOutcome(
                original_query=query,
                normalized_query=normalized,
                expanded_query=expanded,
                retrieval_queries=retrieval_queries,
                classification=classification,
                detected_entities=detected_entities,
                strategy=strategy,
                expansion_rules_applied=rules_applied,
                confidence_prediction=confidence,
                metrics=metrics,
            )
            log_query_processing(outcome, metrics=metrics)
            return outcome
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            outcome = QueryProcessingOutcome.fallback(
                query,
                strategy=default_strategy,
                reason=str(exc),
            )
            metrics = QueryProcessingMetrics(
                classification=outcome.classification.category.value,
                expansion_rules_applied=(),
                generated_query_count=1,
                retrieval_strategy=default_strategy.name,
                processing_latency_ms=latency_ms,
                fallback_used=True,
                fallback_reason=str(exc),
            )
            log_query_processing(outcome, metrics=metrics)
            return outcome
