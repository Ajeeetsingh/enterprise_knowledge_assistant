"""Metadata signal scoring for retrieval rescoring."""

from __future__ import annotations

import math
import re

from app.ingestion.chunker import DocumentChunk
from app.ingestion.semantic_chunking.types import ChunkMetadata, ChunkType
from app.rag.metadata_retrieval.config import MetadataRetrievalSettings
from app.rag.metadata_retrieval.intent import IntentDetectionResult, QueryIntent
from app.ingestion.vector_store.candidates import VectorSearchCandidate
from app.rag.metadata_retrieval.types import MetadataScoreBreakdown

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _apply_soft_ceiling(raw_bonus: float, ceiling: float) -> float:
    """Bound an additive metadata bonus without flattening relative order.

    A hard ``min(raw_bonus, ceiling)`` clip collapses *every* candidate whose
    combined signals exceed the ceiling to the exact same capped value —
    which silently discards the very distinction this scorer exists to make
    whenever two competing chunks (e.g. two headings that both genuinely
    match the query well) each accumulate more bonus than the ceiling
    allows. A smooth saturating curve (scaled ``tanh``) stays strictly
    monotonic in ``raw_bonus`` — a stronger match always yields a strictly
    larger bonus — while still asymptotically bounded by ``ceiling``, so the
    metadata bonus can never override the cross-encoder/cosine signal by
    more than intended. This requires no per-document tuning and applies
    uniformly to any weight configuration.
    """
    if ceiling <= 0:
        return 0.0
    if raw_bonus <= 0:
        return 0.0
    return ceiling * math.tanh(raw_bonus / ceiling)


def _tokenize(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.lower()) if len(token) > 2}


def _overlap_score(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(intersection) / len(union)


def _chunk_metadata(chunk: DocumentChunk) -> ChunkMetadata | None:
    metadata = chunk.metadata
    if isinstance(metadata, ChunkMetadata):
        return metadata
    return None


def _hierarchy_text(metadata: ChunkMetadata | None) -> str:
    if metadata is None or not metadata.hierarchy_path:
        return ""
    return " ".join(metadata.hierarchy_path)


def _chunk_type_value(metadata: ChunkMetadata | None) -> str | None:
    if metadata is None:
        return None
    return metadata.chunk_type.value


def _intent_chunk_type_bonus(
    intent: QueryIntent,
    metadata: ChunkMetadata | None,
    settings: MetadataRetrievalSettings,
) -> tuple[float, list[str]]:
    if metadata is None:
        return 0.0, []

    explanations: list[str] = []
    bonus = 0.0
    chunk_type = metadata.chunk_type

    if intent == QueryIntent.LIST_INTENT and (
        chunk_type == ChunkType.LIST or metadata.contains_list
    ):
        bonus += settings.list_intent_boost
        explanations.append(f"List intent boost (+{settings.list_intent_boost:.2f})")

    if intent == QueryIntent.TABLE_INTENT and (
        chunk_type == ChunkType.TABLE or metadata.contains_table
    ):
        bonus += settings.table_intent_boost
        explanations.append(f"Table intent boost (+{settings.table_intent_boost:.2f})")

    if intent == QueryIntent.SECTION_LOOKUP and chunk_type in {
        ChunkType.SECTION_HEADER,
        ChunkType.SUBSECTION,
    }:
        bonus += settings.section_header_intent_boost
        explanations.append(
            f"Section header intent boost (+{settings.section_header_intent_boost:.2f})"
        )

    if intent == QueryIntent.ENTITY_LOOKUP and chunk_type == ChunkType.PARAGRAPH:
        bonus += settings.paragraph_intent_boost
        explanations.append(
            f"Paragraph entity-lookup boost (+{settings.paragraph_intent_boost:.2f})"
        )

    if intent == QueryIntent.NUMERIC_INTENT and (
        chunk_type == ChunkType.TABLE or metadata.contains_table
    ):
        bonus += settings.numeric_intent_boost
        explanations.append(f"Numeric table boost (+{settings.numeric_intent_boost:.2f})")

    if intent == QueryIntent.GENERAL:
        if chunk_type == ChunkType.PARAGRAPH:
            bonus += settings.paragraph_intent_boost * 0.5
            explanations.append(
                f"General paragraph preference (+{settings.paragraph_intent_boost * 0.5:.2f})"
            )

    return bonus, explanations


def _continuity_bonus(
    candidate: VectorSearchCandidate,
    peers: list[VectorSearchCandidate],
    settings: MetadataRetrievalSettings,
) -> tuple[float, list[str]]:
    metadata = _chunk_metadata(candidate.chunk)
    if metadata is None:
        return 0.0, []

    bonus = 0.0
    explanations: list[str] = []
    section_title = metadata.section_title
    source = candidate.chunk.source
    reading_order = metadata.reading_order

    if section_title:
        section_peers = sum(
            1
            for peer in peers
            if peer is not candidate
            and _chunk_metadata(peer.chunk) is not None
            and _chunk_metadata(peer.chunk).section_title == section_title
        )
        if section_peers >= 1:
            bonus += settings.section_continuity_weight
            explanations.append(
                f"Section continuity '{section_title}' (+{settings.section_continuity_weight:.2f})"
            )

    source_peers = sum(
        1 for peer in peers if peer is not candidate and peer.chunk.source == source
    )
    if source_peers >= 1:
        bonus += settings.document_continuity_weight
        explanations.append(
            f"Document continuity '{source}' (+{settings.document_continuity_weight:.2f})"
        )

    if reading_order is not None:
        adjacent = any(
            peer is not candidate
            and (peer_meta := _chunk_metadata(peer.chunk)) is not None
            and abs(peer_meta.reading_order - reading_order) == 1
            for peer in peers
        )
        if adjacent:
            bonus += settings.reading_order_continuity_weight
            explanations.append(
                "Reading-order continuity (+"
                f"{settings.reading_order_continuity_weight:.2f})"
            )

    return bonus, explanations


def score_candidate(
    query: str,
    candidate: VectorSearchCandidate,
    *,
    intent_result: IntentDetectionResult,
    settings: MetadataRetrievalSettings,
    peers: list[VectorSearchCandidate],
    calibrated_cosine: float,
) -> MetadataScoreBreakdown:
    """Compute metadata bonus and explainability for one candidate."""
    metadata = _chunk_metadata(candidate.chunk)
    explanations: list[str] = []
    bonus = 0.0

    if metadata is not None:
        heading_overlap = _overlap_score(query, metadata.section_title)
        if heading_overlap > 0:
            value = settings.heading_similarity_weight * heading_overlap
            bonus += value
            explanations.append(f"Heading similarity (+{value:.2f})")

        section_overlap = _overlap_score(query, metadata.section_title)
        if section_overlap > 0:
            value = settings.section_title_similarity_weight * section_overlap
            bonus += value
            explanations.append(f"Section-title similarity (+{value:.2f})")

        hierarchy_overlap = _overlap_score(query, _hierarchy_text(metadata))
        if hierarchy_overlap > 0:
            value = settings.hierarchy_similarity_weight * hierarchy_overlap
            bonus += value
            explanations.append(f"Hierarchy similarity (+{value:.2f})")

        if metadata.contains_heading:
            value = settings.chunk_type_match_weight * 0.5
            bonus += value
            explanations.append(f"Contains heading (+{value:.2f})")

    intent_bonus, intent_explanations = _intent_chunk_type_bonus(
        intent_result.primary,
        metadata,
        settings,
    )
    bonus += intent_bonus
    explanations.extend(intent_explanations)

    continuity_bonus, continuity_explanations = _continuity_bonus(
        candidate,
        peers,
        settings,
    )
    bonus += continuity_bonus
    explanations.extend(continuity_explanations)

    bonus = _apply_soft_ceiling(bonus, settings.max_metadata_bonus)
    final_score = min(1.0, calibrated_cosine + bonus)

    return MetadataScoreBreakdown(
        raw_cosine_score=candidate.raw_cosine_score,
        calibrated_cosine_score=calibrated_cosine,
        metadata_bonus=round(bonus, 4),
        final_score=round(final_score, 4),
        explanations=explanations,
        detected_intent=intent_result.primary.value,
        chunk_type=_chunk_type_value(metadata),
    )
