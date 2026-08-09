"""Reranking configuration."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass(frozen=True)
class RerankingSettings:
    """Cross-encoder reranking tunables loaded from application settings."""

    enabled: bool = True
    rerank_top_n: int = 40
    rerank_model_id: str = "ms-marco-minilm-l6-v2"
    max_batch_size: int = 16
    max_sequence_length: int = 512
    registry_path: str | None = None
    # Weight given to the (normalized) metadata bonus — heading/section
    # similarity, chunk-type intent, continuity — when combined with the
    # normalized cross-encoder score to produce the final ranking. The
    # cross-encoder remains the dominant signal; this only lets a strong,
    # generic heading match break ties/close calls the model gets wrong.
    # 0 disables blending and reproduces prior (raw-score-only) behaviour.
    metadata_bonus_weight: float = 0.25
    heading_weighting_enabled: bool = True
    heading_weight_repetitions: int = 2

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> RerankingSettings:
        resolved = settings or get_settings()
        return cls(
            enabled=resolved.reranking_enabled,
            rerank_top_n=resolved.rerank_top_n,
            rerank_model_id=resolved.rerank_model,
            max_batch_size=resolved.rerank_max_batch_size,
            max_sequence_length=resolved.rerank_max_sequence_length,
            metadata_bonus_weight=resolved.rerank_metadata_bonus_weight,
            heading_weighting_enabled=resolved.heading_weighting_enabled,
            heading_weight_repetitions=resolved.heading_weight_repetitions,
        )
