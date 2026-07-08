"""Configuration for hybrid dense + sparse retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass(frozen=True)
class HybridRetrievalSettings:
    """Hybrid retrieval tunables loaded from application settings."""

    enabled: bool = True
    sparse_weight: float = 1.0
    dense_weight: float = 1.0
    rrf_k: int = 60
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    top_k_dense: int = 20
    top_k_sparse: int = 20
    top_k_final: int = 5
    stemming_enabled: bool = False
    stopwords_enabled: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> HybridRetrievalSettings:
        resolved = settings or get_settings()
        return cls(
            enabled=resolved.hybrid_enabled,
            sparse_weight=resolved.sparse_weight,
            dense_weight=resolved.dense_weight,
            rrf_k=resolved.rrf_k,
            bm25_k1=resolved.bm25_k1,
            bm25_b=resolved.bm25_b,
            top_k_dense=resolved.top_k_dense,
            top_k_sparse=resolved.top_k_sparse,
            top_k_final=resolved.top_k_final,
            stemming_enabled=resolved.hybrid_stemming_enabled,
            stopwords_enabled=resolved.hybrid_stopwords_enabled,
        )
