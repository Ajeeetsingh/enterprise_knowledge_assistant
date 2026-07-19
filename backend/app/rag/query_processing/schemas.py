"""Query intelligence data models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QueryCategory(str, Enum):
    """Rule-based query classification categories."""

    ENTITY_LOOKUP = "entity_lookup"
    DEFINITION = "definition"
    NUMERIC = "numeric"
    COMPARISON = "comparison"
    LIST = "list"
    TABLE = "table"
    POLICY = "policy"
    PROCEDURE = "procedure"
    FINANCIAL = "financial"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    CROSS_DOCUMENT = "cross_document"
    GENERAL = "general"


@dataclass(frozen=True)
class ClassificationResult:
    """Outcome of rule-based query classification."""

    category: QueryCategory
    confidence: float
    signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalStrategy:
    """Selected retrieval strategy with effective weight overrides."""

    name: str
    sparse_weight: float
    dense_weight: float
    metadata_bonus_multiplier: float
    rerank_top_n: int
    retrieval_depth_multiplier: float
    explanation: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryProcessingMetrics:
    """Telemetry for one query processing invocation."""

    classification: str
    expansion_rules_applied: tuple[str, ...]
    generated_query_count: int
    retrieval_strategy: str
    processing_latency_ms: float
    fallback_used: bool = False
    fallback_reason: str | None = None


@dataclass(frozen=True)
class QueryProcessingOutcome:
    """Full query intelligence outcome passed to retrieval."""

    original_query: str
    normalized_query: str
    expanded_query: str
    retrieval_queries: tuple[str, ...]
    classification: ClassificationResult
    detected_entities: tuple[str, ...]
    strategy: RetrievalStrategy
    expansion_rules_applied: tuple[str, ...] = ()
    confidence_prediction: float = 0.5
    metrics: QueryProcessingMetrics | None = None
    fallback_used: bool = False

    @classmethod
    def passthrough(cls, query: str, *, strategy: RetrievalStrategy) -> QueryProcessingOutcome:
        """Return a no-op outcome that preserves the original query."""
        classification = ClassificationResult(
            category=QueryCategory.GENERAL,
            confidence=0.5,
            signals=("passthrough",),
        )
        return cls(
            original_query=query,
            normalized_query=query,
            expanded_query=query,
            retrieval_queries=(query,),
            classification=classification,
            detected_entities=(),
            strategy=strategy,
            confidence_prediction=0.5,
        )

    @classmethod
    def fallback(
        cls,
        query: str,
        *,
        strategy: RetrievalStrategy,
        reason: str,
    ) -> QueryProcessingOutcome:
        """Failsafe outcome when processing fails."""
        outcome = cls.passthrough(query, strategy=strategy)
        return QueryProcessingOutcome(
            original_query=outcome.original_query,
            normalized_query=outcome.normalized_query,
            expanded_query=outcome.expanded_query,
            retrieval_queries=outcome.retrieval_queries,
            classification=outcome.classification,
            detected_entities=outcome.detected_entities,
            strategy=strategy,
            fallback_used=True,
            metrics=QueryProcessingMetrics(
                classification=QueryCategory.GENERAL.value,
                expansion_rules_applied=(),
                generated_query_count=1,
                retrieval_strategy=strategy.name,
                processing_latency_ms=0.0,
                fallback_used=True,
                fallback_reason=reason,
            ),
        )
