"""Semantic chunk generation orchestrator."""

from __future__ import annotations

import logging
import time

from app.core.logging import get_logger, log_with_fields
from app.ingestion.chunker import DocumentChunk
from app.ingestion.semantic_chunking.assembler import AssembledChunk, assemble_semantic_chunks
from app.ingestion.semantic_chunking.config import SemanticChunkingSettings
from app.ingestion.semantic_chunking.ids import stable_chunk_id
from app.ingestion.semantic_chunking.types import SemanticChunkStats
from app.ingestion.semantic_chunking.validator import validate_semantic_chunks
from app.ingestion.structure.extractor import StructureExtractor
from app.ingestion.structure.models import StructuredDocument

logger = get_logger(__name__)


class SemanticChunkEngine:
    """Generate semantically meaningful chunks from a structured document."""

    def __init__(
        self,
        settings: SemanticChunkingSettings | None = None,
        structure_extractor: StructureExtractor | None = None,
    ) -> None:
        self._settings = settings or SemanticChunkingSettings.from_settings()
        self._structure_extractor = structure_extractor or StructureExtractor()

    @property
    def settings(self) -> SemanticChunkingSettings:
        return self._settings

    def chunk_document(
        self,
        structured_document: StructuredDocument,
        *,
        source: str,
        category: str,
    ) -> list[DocumentChunk]:
        """Generate document chunks from a structured document."""
        chunks, _stats = self.chunk_document_with_stats(
            structured_document,
            source=source,
            category=category,
        )
        return chunks

    def chunk_from_text(
        self,
        text: str,
        *,
        source: str,
        category: str,
    ) -> list[DocumentChunk]:
        """Build structure from text and generate semantic chunks."""
        structured = self._structure_extractor.extract(text, source)
        return self.chunk_document(structured, source=source, category=category)

    def chunk_document_with_stats(
        self,
        structured_document: StructuredDocument,
        *,
        source: str,
        category: str,
    ) -> tuple[list[DocumentChunk], SemanticChunkStats]:
        started = time.perf_counter()
        assembled = assemble_semantic_chunks(
            structured_document,
            category,
            self._settings,
        )
        assembled = _apply_source_to_chunk_ids(assembled, source)
        issues = validate_semantic_chunks(structured_document, assembled)

        document_chunks: list[DocumentChunk] = []
        for index, chunk in enumerate(assembled):
            document_chunks.append(
                DocumentChunk(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content,
                    source=source,
                    category=category,
                    chunk_index=index,
                    page_number=chunk.page_number,
                    metadata=chunk.metadata,
                )
            )

        stats = _build_stats(document_chunks, time.perf_counter() - started)
        if document_chunks:
            log_with_fields(
                logger,
                logging.INFO,
                "Semantic chunk generation completed",
                source=source,
                chunks_created=stats.chunks_created,
                average_chunk_size=round(stats.average_chunk_size, 1),
                median_chunk_size=round(stats.median_chunk_size, 1),
                largest_chunk=stats.largest_chunk,
                smallest_chunk=stats.smallest_chunk,
                average_words=round(stats.average_words, 1),
                average_paragraphs=round(stats.average_paragraphs, 2),
                average_tables=round(stats.average_tables, 2),
                chunk_type_distribution=stats.chunk_type_distribution,
                duration_ms=stats.duration_ms,
                validation_issue_count=len(issues),
            )
        if issues:
            log_with_fields(
                logger,
                logging.WARNING,
                "Semantic chunk validation warnings",
                source=source,
                issue_count=len(issues),
            )
        return document_chunks, stats


def _apply_source_to_chunk_ids(chunks: list[AssembledChunk], source: str) -> list[AssembledChunk]:
    for chunk in chunks:
        chunk.chunk_id = stable_chunk_id(source, chunk.blocks)
    return chunks


def _build_stats(chunks: list[DocumentChunk], elapsed_seconds: float) -> SemanticChunkStats:
    if not chunks:
        return SemanticChunkStats(duration_ms=round(elapsed_seconds * 1000, 3))

    sizes = [len(chunk.content) for chunk in chunks]
    words = [len(chunk.content.split()) for chunk in chunks]
    paragraphs = [
        chunk.metadata.paragraph_count if chunk.metadata is not None else 0
        for chunk in chunks
    ]
    tables = [
        chunk.metadata.table_count if chunk.metadata is not None else 0
        for chunk in chunks
    ]
    distribution: dict[str, int] = {}
    for chunk in chunks:
        if chunk.metadata is None:
            continue
        key = chunk.metadata.chunk_type.value
        distribution[key] = distribution.get(key, 0) + 1

    count = len(chunks)
    sorted_sizes = sorted(sizes)
    median = sorted_sizes[count // 2] if count % 2 else (
        (sorted_sizes[count // 2 - 1] + sorted_sizes[count // 2]) / 2
    )
    return SemanticChunkStats(
        chunks_created=count,
        average_chunk_size=sum(sizes) / count,
        median_chunk_size=float(median),
        largest_chunk=max(sizes),
        smallest_chunk=min(sizes),
        average_words=sum(words) / count,
        average_paragraphs=sum(paragraphs) / count,
        average_tables=sum(tables) / count,
        chunk_type_distribution=distribution,
        duration_ms=round(elapsed_seconds * 1000, 3),
    )
