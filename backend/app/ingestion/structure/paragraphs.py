"""Paragraph detection and preservation."""

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.structure.line_stream import AnnotatedLine


@dataclass
class DetectedParagraph:
    """A paragraph block detected in the line stream."""

    start_line_index: int
    end_line_index: int
    text: str
    page_start: int | None
    page_end: int | None


def detect_paragraphs(
    lines: list[AnnotatedLine],
    consumed_line_indexes: set[int],
) -> list[DetectedParagraph]:
    """Detect paragraph blocks from remaining unconsumed lines."""
    paragraphs: list[DetectedParagraph] = []
    buffer: list[AnnotatedLine] = []

    def flush() -> None:
        if not buffer:
            return
        text = " ".join(line.text.strip() for line in buffer if line.text.strip())
        if text:
            paragraphs.append(
                DetectedParagraph(
                    start_line_index=buffer[0].index,
                    end_line_index=buffer[-1].index,
                    text=text,
                    page_start=buffer[0].page,
                    page_end=buffer[-1].page,
                )
            )
        buffer.clear()

    for line in lines:
        if line.is_blank:
            flush()
            continue
        if line.index in consumed_line_indexes:
            flush()
            continue
        buffer.append(line)
    flush()
    return paragraphs
