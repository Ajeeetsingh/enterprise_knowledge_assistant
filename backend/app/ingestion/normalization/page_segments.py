"""Page segmentation helpers for marker-aware normalization."""

from __future__ import annotations

import re

from app.ingestion.normalization.types import PageSegment

_PAGE_MARKER_RE = re.compile(r"^<<<PAGE:(\d+)>>>$")


def is_page_marker(line: str) -> bool:
    """Return True when *line* is a parser-generated page marker."""
    return bool(_PAGE_MARKER_RE.match(line.strip()))


def split_into_pages(text: str) -> list[PageSegment]:
    """Split extracted text into page segments while preserving markers."""
    segments: list[PageSegment] = []
    current_marker: str | None = None
    current_lines: list[str] = []

    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if is_page_marker(stripped):
            if current_marker is not None or current_lines:
                segments.append(PageSegment(marker=current_marker, lines=current_lines))
            current_marker = stripped
            current_lines = []
            continue
        current_lines.append(raw_line.rstrip("\r"))

    if current_marker is not None or current_lines:
        segments.append(PageSegment(marker=current_marker, lines=current_lines))

    return segments


def join_pages(segments: list[PageSegment]) -> str:
    """Reassemble page segments into canonical plain text."""
    blocks: list[str] = []
    for segment in segments:
        if segment.marker:
            blocks.append(segment.marker)
        if segment.lines:
            blocks.append("\n".join(segment.lines))
    return "\n".join(block for block in blocks if block)


_PAGE_NUMBER_TOKEN_RE = re.compile(
    r"\bpage\s*[:\-]?\s*\d+\s*(?:of\s*\d+)?\b|\b\d+\s*/\s*\d+\b",
    re.IGNORECASE,
)


def normalize_line_key(line: str) -> str:
    """Normalize a line for cross-page frequency comparison."""
    collapsed = " ".join(line.split()).strip().lower()
    return collapsed


def boilerplate_line_key(line: str) -> str:
    """Normalize a line for boilerplate frequency comparison.

    Page-number tokens are masked so footers like ``Page 8 of 15`` and
    ``Page 9 of 15`` collapse to the same key.
    """
    key = normalize_line_key(line)
    return _PAGE_NUMBER_TOKEN_RE.sub("{page}", key)
