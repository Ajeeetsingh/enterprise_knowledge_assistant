"""Reranking configuration."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass(frozen=True)
class RerankingSettings:
    """Cross-encoder reranking tunables loaded from application settings."""

    enabled: bool = True
    rerank_top_n: int = 20
    rerank_model_id: str = "ms-marco-minilm-l6-v2"
    max_batch_size: int = 16
    max_sequence_length: int = 512
    registry_path: str | None = None

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> RerankingSettings:
        resolved = settings or get_settings()
        return cls(
            enabled=resolved.reranking_enabled,
            rerank_top_n=resolved.rerank_top_n,
            rerank_model_id=resolved.rerank_model,
            max_batch_size=resolved.rerank_max_batch_size,
            max_sequence_length=resolved.rerank_max_sequence_length,
        )
