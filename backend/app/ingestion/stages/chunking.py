"""Document chunking stage."""

from __future__ import annotations

from app.core.exceptions import DocumentIngestionError
from app.documents.types import IngestionContext
from app.ingestion.categorizer import resolve_category
from app.ingestion.chunker import chunk_text
from app.ingestion.stages.base import PipelineStage


class ChunkingStage(PipelineStage):
    """Split extracted text into retrieval-ready ``DocumentChunk`` objects."""

    @property
    def name(self) -> str:
        return "chunking"

    @property
    def description(self) -> str:
        return "Split extracted text into semantic chunks for retrieval."

    @property
    def order(self) -> int:
        return 4

    def process(self, context: IngestionContext) -> IngestionContext:
        if context.extracted_text is None:
            raise DocumentIngestionError(
                "Extracted text is required before chunking. "
                "Ensure ExtractionStage runs before ChunkingStage."
            )

        category = resolve_category(context.filename)
        context.chunks = chunk_text(
            context.extracted_text,
            source=context.filename,
            category=category,
        )
        context.chunk_count = len(context.chunks)
        context.stage_results[self.name] = f"chunked:{context.chunk_count}"
        return context
