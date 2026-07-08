"""Configuration for semantic chunk generation."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass(frozen=True)
class SemanticChunkingSettings:
    """Configurable thresholds for semantic chunk generation."""

    max_preferred_chunk_size: int = 1200
    min_chunk_size: int = 80
    soft_max_chunk_size: int = 1500
    absolute_max_chunk_size: int = 1800
    max_table_chunk_size: int = 1800
    max_paragraph_merge: int = 2
    section_merge_threshold: int = 1800
    semantic_overlap_enabled: bool = True
    include_hierarchy_in_overlap: bool = True

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> SemanticChunkingSettings:
        """Build semantic chunking settings from application config."""
        resolved = settings or get_settings()
        return cls(
            max_preferred_chunk_size=resolved.semantic_max_preferred_chunk_size,
            min_chunk_size=resolved.semantic_min_chunk_size,
            soft_max_chunk_size=resolved.semantic_soft_max_chunk_size,
            absolute_max_chunk_size=resolved.semantic_absolute_max_chunk_size,
            max_table_chunk_size=resolved.semantic_max_table_chunk_size,
            max_paragraph_merge=resolved.semantic_max_paragraph_merge,
            section_merge_threshold=resolved.semantic_section_merge_threshold,
            semantic_overlap_enabled=resolved.semantic_overlap_enabled,
            include_hierarchy_in_overlap=resolved.semantic_include_hierarchy_in_overlap,
        )
