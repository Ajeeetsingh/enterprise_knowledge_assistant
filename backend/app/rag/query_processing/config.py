"""Query intelligence configuration."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass(frozen=True)
class QueryProcessingSettings:
    """Query intelligence tunables loaded from application settings."""

    enabled: bool = True
    query_expansion_enabled: bool = True
    multi_query_enabled: bool = True
    max_generated_queries: int = 4
    entity_normalization_enabled: bool = True
    synonym_expansion_enabled: bool = True
    strategy_selection_enabled: bool = True
    registry_path: str | None = None

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> QueryProcessingSettings:
        resolved = settings or get_settings()
        return cls(
            enabled=resolved.query_intelligence_enabled,
            query_expansion_enabled=resolved.query_expansion_enabled,
            multi_query_enabled=resolved.multi_query_enabled,
            max_generated_queries=resolved.max_generated_queries,
            entity_normalization_enabled=resolved.entity_normalization_enabled,
            synonym_expansion_enabled=resolved.synonym_expansion_enabled,
            strategy_selection_enabled=resolved.strategy_selection_enabled,
        )
