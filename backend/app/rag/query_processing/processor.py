"""Query intelligence orchestrator."""

from __future__ import annotations

import re
import time

from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.query_processing.classifier import classify_query
from app.rag.query_processing.config import QueryProcessingSettings
from app.rag.query_processing.enterprise_expansion import expand_from_understanding
from app.rag.query_processing.expander import expand_query, generate_retrieval_queries
from app.rag.query_processing.metrics import log_query_processing
from app.rag.query_processing.registry import StrategySpec, get_rules
from app.rag.query_processing.schemas import (
    QueryProcessingMetrics,
    QueryProcessingOutcome,
    RetrievalStrategy,
)
from app.rag.query_processing.strategy import select_strategy
from app.rag.query_processing.understanding import understand_query
from app.rag.reranking.config import RerankingSettings


def _predict_confidence(
    classification_confidence: float,
    *,
    query_count: int,
    rules_applied: int,
    understanding_confidence: float = 0.0,
) -> float:
    boost = min(0.15, rules_applied * 0.02)
    multi_query_boost = 0.05 if query_count > 1 else 0.0
    understanding_boost = min(0.1, understanding_confidence * 0.1)
    return round(
        min(0.95, classification_confidence + boost + multi_query_boost + understanding_boost),
        4,
    )


def _merge_retrieval_queries(
    *groups: tuple[str, ...],
    max_queries: int,
    original_query: str,
) -> tuple[str, ...]:
    """Deduplicate retrieval queries, keeping the original question first."""
    ordered: list[str] = []
    seen: set[str] = set()

    def _add(query: str) -> None:
        key = re.sub(r"\s+", " ", query.strip().lower())
        if not key or key in seen:
            return
        seen.add(key)
        ordered.append(query.strip())

    _add(original_query)
    for group in groups:
        for query in group:
            if len(ordered) >= max_queries:
                break
            _add(query)
        if len(ordered) >= max_queries:
            break
    return tuple(ordered or (original_query,))


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
            understanding = understand_query(query, classification=classification)

            normalized, expanded, detected_entities, legacy_rules = expand_query(
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

            legacy_queries = generate_retrieval_queries(
                original_query=query,
                normalized_query=normalized,
                expanded_query=expanded,
                classification=classification,
                detected_entities=detected_entities,
                registry=self._registry,
                settings=self._settings,
            )

            enterprise_queries: tuple[str, ...] = ()
            enterprise_rules: tuple[str, ...] = ()
            expansion_strategy = "legacy_rules"
            if self._settings.query_expansion_enabled or self._settings.multi_query_enabled:
                enterprise_queries, enterprise_rules, expansion_strategy = expand_from_understanding(
                    original_query=query,
                    understanding=understanding,
                    max_queries=self._settings.max_generated_queries,
                )

            retrieval_queries = _merge_retrieval_queries(
                enterprise_queries,
                legacy_queries,
                max_queries=self._settings.max_generated_queries,
                original_query=query,
            )

            # Prefer enterprise understanding entities when richer.
            merged_entities = tuple(
                dict.fromkeys([*understanding.entities, *detected_entities])
            )
            rules_applied = tuple(dict.fromkeys([*enterprise_rules, *legacy_rules]))

            # Surface a compact expanded string for telemetry (not used as LLM prompt).
            if len(retrieval_queries) > 1:
                expanded_for_retrieval = " | ".join(retrieval_queries[1:4])
            else:
                expanded_for_retrieval = expanded

            confidence = _predict_confidence(
                classification.confidence,
                query_count=len(retrieval_queries),
                rules_applied=len(rules_applied),
                understanding_confidence=understanding.confidence,
            )
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            metrics = QueryProcessingMetrics(
                classification=classification.category.value,
                expansion_rules_applied=rules_applied,
                generated_query_count=len(retrieval_queries),
                retrieval_strategy=strategy.name,
                processing_latency_ms=latency_ms,
                expansion_strategy=expansion_strategy,
                understanding_intent=understanding.intent,
            )
            outcome = QueryProcessingOutcome(
                original_query=query,
                normalized_query=normalized,
                expanded_query=expanded_for_retrieval,
                retrieval_queries=retrieval_queries,
                classification=classification,
                detected_entities=merged_entities,
                strategy=strategy,
                expansion_rules_applied=rules_applied,
                confidence_prediction=confidence,
                metrics=metrics,
                understanding_intent=understanding.intent,
                understanding_concepts=understanding.concepts,
                understanding_likely_documents=understanding.likely_documents,
                expansion_strategy=expansion_strategy,
            )
            log_query_processing(outcome, metrics=metrics, understanding=understanding)
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
