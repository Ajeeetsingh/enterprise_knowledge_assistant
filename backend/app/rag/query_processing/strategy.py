"""Retrieval strategy selection."""

from __future__ import annotations

from dataclasses import replace

from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.query_processing.config import QueryProcessingSettings
from app.rag.query_processing.registry import QueryRulesRegistry, StrategySpec
from app.rag.query_processing.schemas import ClassificationResult, QueryCategory, RetrievalStrategy
from app.rag.reranking.config import RerankingSettings


def _default_strategy() -> RetrievalStrategy:
    return RetrievalStrategy(
        name=QueryCategory.GENERAL.value,
        sparse_weight=1.0,
        dense_weight=1.0,
        metadata_bonus_multiplier=1.0,
        rerank_top_n=20,
        retrieval_depth_multiplier=1.0,
        explanation=("default_strategy",),
    )


def _resolve_strategy_spec(
    classification: ClassificationResult,
    registry: QueryRulesRegistry,
) -> StrategySpec:
    key = classification.category.value
    return registry.strategies.get(key) or registry.strategies.get(
        QueryCategory.GENERAL.value,
        StrategySpec(name=QueryCategory.GENERAL.value),
    )


def select_strategy(
    classification: ClassificationResult,
    *,
    registry: QueryRulesRegistry,
    hybrid_settings: HybridRetrievalSettings,
    metadata_settings: MetadataRetrievalSettings,
    reranking_settings: RerankingSettings,
    settings: QueryProcessingSettings,
) -> RetrievalStrategy:
    """Select retrieval strategy and compute effective weight overrides."""
    if not settings.strategy_selection_enabled:
        return _default_strategy()

    spec = _resolve_strategy_spec(classification, registry)
    sparse = round(hybrid_settings.sparse_weight * spec.sparse_weight_multiplier, 4)
    dense = round(hybrid_settings.dense_weight * spec.dense_weight_multiplier, 4)
    rerank_top_n = spec.rerank_top_n or reranking_settings.rerank_top_n

    explanation = (
        f"classification={classification.category.value}",
        f"sparse_weight={sparse}",
        f"dense_weight={dense}",
        f"metadata_bonus_multiplier={spec.metadata_bonus_multiplier}",
        f"rerank_top_n={rerank_top_n}",
        f"retrieval_depth_multiplier={spec.retrieval_depth_multiplier}",
    )
    return RetrievalStrategy(
        name=spec.name,
        sparse_weight=sparse,
        dense_weight=dense,
        metadata_bonus_multiplier=spec.metadata_bonus_multiplier,
        rerank_top_n=rerank_top_n,
        retrieval_depth_multiplier=spec.retrieval_depth_multiplier,
        explanation=explanation,
    )


def apply_strategy_to_hybrid_settings(
    base: HybridRetrievalSettings,
    strategy: RetrievalStrategy,
) -> HybridRetrievalSettings:
    """Return hybrid settings with strategy overrides applied."""
    depth_mult = strategy.retrieval_depth_multiplier
    dense_k = max(5, int(round(base.top_k_dense * depth_mult)))
    sparse_k = max(5, int(round(base.top_k_sparse * depth_mult)))
    return replace(
        base,
        sparse_weight=strategy.sparse_weight,
        dense_weight=strategy.dense_weight,
        top_k_dense=dense_k,
        top_k_sparse=sparse_k,
    )


def apply_strategy_to_metadata_settings(
    base: MetadataRetrievalSettings,
    strategy: RetrievalStrategy,
) -> MetadataRetrievalSettings:
    """Return metadata settings with strategy multiplier applied."""
    multiplier = strategy.metadata_bonus_multiplier
    return replace(
        base,
        max_metadata_bonus=round(base.max_metadata_bonus * multiplier, 4),
        heading_similarity_weight=round(base.heading_similarity_weight * multiplier, 4),
        section_title_similarity_weight=round(
            base.section_title_similarity_weight * multiplier, 4
        ),
        hierarchy_similarity_weight=round(base.hierarchy_similarity_weight * multiplier, 4),
        chunk_type_match_weight=round(base.chunk_type_match_weight * multiplier, 4),
    )


def apply_strategy_to_rerank_settings(
    base: RerankingSettings,
    strategy: RetrievalStrategy,
) -> RerankingSettings:
    return replace(base, rerank_top_n=strategy.rerank_top_n)
