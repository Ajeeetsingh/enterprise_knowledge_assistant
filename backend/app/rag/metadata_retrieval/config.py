"""Configuration for metadata-aware retrieval rescoring."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass(frozen=True)
class MetadataRetrievalSettings:
    """Configurable metadata signal weights for retrieval rescoring."""

    enabled: bool = True
    candidate_multiplier: int = 15
    max_metadata_bonus: float = 0.15

    heading_similarity_weight: float = 0.04
    section_title_similarity_weight: float = 0.05
    hierarchy_similarity_weight: float = 0.03
    chunk_type_match_weight: float = 0.04

    table_intent_boost: float = 0.05
    list_intent_boost: float = 0.05
    section_header_intent_boost: float = 0.04
    paragraph_intent_boost: float = 0.04
    numeric_intent_boost: float = 0.03

    section_continuity_weight: float = 0.03
    document_continuity_weight: float = 0.02
    reading_order_continuity_weight: float = 0.02

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> MetadataRetrievalSettings:
        resolved = settings or get_settings()
        return cls(
            enabled=resolved.metadata_retrieval_enabled,
            candidate_multiplier=resolved.metadata_candidate_multiplier,
            max_metadata_bonus=resolved.metadata_max_bonus,
            heading_similarity_weight=resolved.metadata_heading_similarity_weight,
            section_title_similarity_weight=resolved.metadata_section_title_similarity_weight,
            hierarchy_similarity_weight=resolved.metadata_hierarchy_similarity_weight,
            chunk_type_match_weight=resolved.metadata_chunk_type_match_weight,
            table_intent_boost=resolved.metadata_table_intent_boost,
            list_intent_boost=resolved.metadata_list_intent_boost,
            section_header_intent_boost=resolved.metadata_section_header_intent_boost,
            paragraph_intent_boost=resolved.metadata_paragraph_intent_boost,
            numeric_intent_boost=resolved.metadata_numeric_intent_boost,
            section_continuity_weight=resolved.metadata_section_continuity_weight,
            document_continuity_weight=resolved.metadata_document_continuity_weight,
            reading_order_continuity_weight=resolved.metadata_reading_order_continuity_weight,
        )
