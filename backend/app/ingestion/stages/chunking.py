"""Document chunking stage."""

from __future__ import annotations

import logging

from app.core.exceptions import DocumentIngestionError
from app.core.logging import get_logger, log_with_fields
from app.documents.types import IngestionContext
from app.ingestion.categorizer import resolve_category
from app.ingestion.semantic_chunking import SemanticChunkEngine
from app.ingestion.stages.base import PipelineStage
from app.ingestion.structure.extractor import StructureExtractor

logger = get_logger(__name__)


class ChunkingStage(PipelineStage):
    """Generate retrieval-ready semantic chunks from structured documents."""

    def __init__(
        self,
        chunk_engine: SemanticChunkEngine | None = None,
        structure_extractor: StructureExtractor | None = None,
    ) -> None:
        self._structure_extractor = structure_extractor or StructureExtractor()
        self._chunk_engine = chunk_engine or SemanticChunkEngine(
            structure_extractor=self._structure_extractor
        )

    @property
    def name(self) -> str:
        return "chunking"

    @property
    def description(self) -> str:
        return "Generate semantic chunks from structured document blocks."

    @property
    def order(self) -> int:
        return 4

    def process(self, context: IngestionContext) -> IngestionContext:
        if context.extracted_text is None:
            raise DocumentIngestionError(
                "Extracted text is required before chunking. "
                "Ensure ExtractionStage runs before ChunkingStage."
            )

        structured_document = context.structured_document
        if structured_document is None:
            structured_document = self._structure_extractor.extract(
                context.extracted_text,
                context.filename,
            )
            context.structured_document = structured_document

        category = resolve_category(context.filename)
        context.chunks, stats = self._chunk_engine.chunk_document_with_stats(
            structured_document,
            source=context.filename,
            category=category,
        )
        context.chunk_count = stats.chunks_created
        if context.chunk_count == 0:
            raise DocumentIngestionError(
                "Semantic chunking produced no searchable segments after text extraction."
            )

        log_with_fields(
            logger,
            logging.INFO,
            "Document chunking completed",
            document_id=context.document_id,
            filename=context.filename,
            chunk_count=context.chunk_count,
            average_chunk_size=round(stats.average_chunk_size, 1),
            largest_chunk=stats.largest_chunk,
            smallest_chunk=stats.smallest_chunk,
            chunk_type_distribution=stats.chunk_type_distribution,
            category=category,
            first_chunk_preview=context.chunks[0].content[:500],
        )
        context.stage_results[self.name] = f"chunked:{context.chunk_count}"
        return context
