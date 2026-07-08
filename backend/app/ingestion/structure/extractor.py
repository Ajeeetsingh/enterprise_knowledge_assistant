"""Structure extraction orchestrator."""

from __future__ import annotations

import logging
import time

from app.core.logging import get_logger, log_with_fields
from app.ingestion.structure.config import StructureExtractionSettings
from app.ingestion.structure.headings import detect_headings
from app.ingestion.structure.line_stream import parse_line_stream
from app.ingestion.structure.lists import detect_lists
from app.ingestion.structure.models import (
    BlockType,
    StructuredDocument,
    StructureStats,
)
from app.ingestion.structure.paragraphs import detect_paragraphs
from app.ingestion.structure.sections import (
    build_sections,
    hierarchy_depth,
    make_document_blocks,
)
from app.ingestion.structure.tables import detect_tables
from app.ingestion.structure.validator import validate_structure

logger = get_logger(__name__)


class StructureExtractor:
    """Extract hierarchical document structure from normalized text."""

    def __init__(self, settings: StructureExtractionSettings | None = None) -> None:
        self._settings = settings or StructureExtractionSettings()

    @property
    def settings(self) -> StructureExtractionSettings:
        return self._settings

    def extract(self, text: str, source: str) -> StructuredDocument:
        """Build a structured document from normalized plain text."""
        document, _issues = self.extract_with_validation(text, source)
        return document

    def extract_with_validation(
        self,
        text: str,
        source: str,
    ) -> tuple[StructuredDocument, list[str]]:
        """Build a structured document and return validation issues."""
        started = time.perf_counter()
        settings = self._settings

        lines = parse_line_stream(text)
        headings = detect_headings(lines, settings)
        heading_indexes = {heading.line_index for heading in headings}
        tables = detect_tables(lines, settings)
        lists = detect_lists(lines, settings, skip_line_indexes=heading_indexes)

        consumed_indexes: set[int] = set()
        for table in tables:
            for line in lines:
                if table.start_line_index <= line.index <= table.end_line_index:
                    consumed_indexes.add(line.index)
        for list_block in lists:
            for line in lines:
                if list_block.start_line_index <= line.index <= list_block.end_line_index:
                    consumed_indexes.add(line.index)
        for heading in headings:
            consumed_indexes.add(heading.line_index)
            # Split headings consume the title line immediately following the number.
            if heading.section_number and heading.text.startswith(f"{heading.section_number} "):
                title_suffix = heading.text[len(heading.section_number) :].strip()
                for line in lines:
                    if line.text == title_suffix and line.index > heading.line_index:
                        consumed_indexes.add(line.index)
                        break

        paragraphs = detect_paragraphs(lines, consumed_indexes)
        blocks = make_document_blocks(headings, tables, lists, paragraphs)
        sections = build_sections(headings, blocks)

        stats = StructureStats(
            sections_detected=_count_sections(sections),
            tables_detected=sum(1 for block in blocks if block.block_type == BlockType.TABLE),
            lists_detected=sum(1 for block in blocks if block.block_type == BlockType.LIST),
            headings_detected=sum(1 for block in blocks if block.block_type == BlockType.HEADING),
            paragraphs_detected=sum(1 for block in blocks if block.block_type == BlockType.PARAGRAPH),
            hierarchy_depth=hierarchy_depth(sections),
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
        )

        document = StructuredDocument(
            source=source,
            sections=sections,
            blocks=blocks,
            stats=stats,
            raw_text=text,
        )
        issues = validate_structure(document)

        if stats.sections_detected or stats.headings_detected:
            log_with_fields(
                logger,
                logging.INFO,
                "Document structure extraction completed",
                source=source,
                sections_detected=stats.sections_detected,
                tables_detected=stats.tables_detected,
                lists_detected=stats.lists_detected,
                headings_detected=stats.headings_detected,
                hierarchy_depth=stats.hierarchy_depth,
                duration_ms=stats.duration_ms,
                validation_issue_count=len(issues),
            )

        return document, issues


def _count_sections(sections: list) -> int:
    count = 0
    for section in sections:
        count += 1
        count += _count_sections(section.subsections)
    return count
