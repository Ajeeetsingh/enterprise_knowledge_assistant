"""Text extraction stage."""

from __future__ import annotations

import logging

from app.core.exceptions import DocumentIngestionError
from app.core.logging import get_logger, log_with_fields
from app.documents.types import IngestionContext
from app.ingestion.processor import DocumentProcessor
from app.ingestion.stages.base import PipelineStage
from app.ingestion.structure.config import StructureExtractionSettings
from app.ingestion.structure.extractor import StructureExtractor

logger = get_logger(__name__)


class ExtractionStage(PipelineStage):
    """Extract and normalize text using the configured ``DocumentProcessor``.

    Separating extraction into a dedicated stage and depending on the
    ``DocumentProcessor`` abstraction means the extraction strategy is fully
    replaceable (OCR, HTML, Markdown…) without touching pipeline logic.
    """

    def __init__(
        self,
        processor: DocumentProcessor,
        structure_extractor: StructureExtractor | None = None,
        structure_settings: StructureExtractionSettings | None = None,
    ) -> None:
        self._processor = processor
        self._structure_settings = structure_settings or StructureExtractionSettings.from_settings()
        self._structure_extractor = structure_extractor or StructureExtractor(
            settings=self._structure_settings
        )

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
        text = context.extracted_text or ""
        char_count = len(text)
        preview = text[:500]

        if self._structure_settings.enabled:
            structured, issues = self._structure_extractor.extract_with_validation(
                text,
                context.filename,
            )
            context.structured_document = structured
            context.stage_results[self.name] = (
                f"extracted:{char_count};structured:{structured.stats.sections_detected}"
            )
            if issues:
                log_with_fields(
                    logger,
                    logging.WARNING,
                    "Structure extraction validation warnings",
                    document_id=context.document_id,
                    filename=context.filename,
                    issue_count=len(issues),
                )
        else:
            context.stage_results[self.name] = f"extracted:{char_count}"

        log_with_fields(
            logger,
            logging.INFO,
            "Text extraction completed",
            document_id=context.document_id,
            filename=context.filename,
            characters_extracted=char_count,
            text_preview=preview,
            sections_detected=(
                context.structured_document.stats.sections_detected
                if context.structured_document is not None
                else 0
            ),
            tables_detected=(
                context.structured_document.stats.tables_detected
                if context.structured_document is not None
                else 0
            ),
            lists_detected=(
                context.structured_document.stats.lists_detected
                if context.structured_document is not None
                else 0
            ),
            headings_detected=(
                context.structured_document.stats.headings_detected
                if context.structured_document is not None
                else 0
            ),
        )

        if char_count == 0:
            raise DocumentIngestionError(
                "Text extraction produced no usable content. "
                "The document cannot be indexed."
            )

        return context
