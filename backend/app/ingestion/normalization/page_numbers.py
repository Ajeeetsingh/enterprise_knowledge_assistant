"""Page number line removal."""

from __future__ import annotations

import re

from app.ingestion.normalization.types import CleaningStats, PageSegment

_PAGE_NUMBER_PATTERNS = (
    re.compile(r"^page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^page\s*[:\-]?\s*\d+\s*$", re.IGNORECASE),
    re.compile(r"^\d+\s*/\s*\d+\s*$"),
    re.compile(r"^page\s+\d+\s+of\s+\d+\s*[|\-].*$", re.IGNORECASE),
)


def _is_page_number_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(pattern.match(stripped) for pattern in _PAGE_NUMBER_PATTERNS)


def remove_page_numbers(segments: list[PageSegment]) -> CleaningStats:
    """Remove standalone page-number lines without touching page markers."""
    stats = CleaningStats(pages_processed=len(segments))
    for segment in segments:
        cleaned: list[str] = []
        for line in segment.lines:
            if _is_page_number_line(line):
                stats.page_numbers_removed += 1
                stats.characters_removed += len(line)
                continue
            cleaned.append(line)
        segment.lines = cleaned
    return stats
