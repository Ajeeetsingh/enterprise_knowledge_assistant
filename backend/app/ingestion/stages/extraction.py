"""Text extraction stage."""

from __future__ import annotations

from app.documents.types import IngestionContext
from app.ingestion.processor import DocumentProcessor
from app.ingestion.stages.base import PipelineStage


class ExtractionStage(PipelineStage):
    """Extract and normalize text using the configured ``DocumentProcessor``.

    Separating extraction into a dedicated stage and depending on the
    ``DocumentProcessor`` abstraction means the extraction strategy is fully
    replaceable (OCR, HTML, Markdown…) without touching pipeline logic.
    """

    def __init__(self, processor: DocumentProcessor) -> None:
        self._processor = processor

    @property
    def name(self) -> str:
        return "extraction"

    @property
    def description(self) -> str:
        return "Extract and normalise plain text from the document."

    @property
    def order(self) -> int:
        return 3

    def process(self, context: IngestionContext) -> IngestionContext:
        context.extracted_text = self._processor.process(context)
        context.stage_results[self.name] = "extracted"
        return context
