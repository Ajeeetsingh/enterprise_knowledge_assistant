"""Frequency-based boilerplate detection and removal."""

from __future__ import annotations

import re
from collections import Counter

from app.ingestion.normalization.config import NormalizationSettings
from app.ingestion.normalization.page_segments import boilerplate_line_key
from app.ingestion.normalization.types import CleaningStats, PageSegment

_PAGE_NUMBER_RE = re.compile(
    r"^(?:page\s*[:\-]?\s*\d+\s*(?:of\s*\d+)?|\d+\s*/\s*\d+)$",
    re.IGNORECASE,
)
_CLASSIFICATION_RE = re.compile(
    r"^(?:classification|classified|confidential|internal use only|strictly confidential)\b",
    re.IGNORECASE,
)
_COPYRIGHT_RE = re.compile(
    r"(?:©|copyright)\s*\d{4}",
    re.IGNORECASE,
)
_VERSION_RE = re.compile(
    r"\bversion\s+\d+(?:\.\d+)*\b",
    re.IGNORECASE,
)


def _candidate_header_lines(segment: PageSegment, max_lines: int) -> list[str]:
    non_empty = [line for line in segment.lines if line.strip()]
    return non_empty[:max_lines]


def _candidate_footer_lines(segment: PageSegment, max_lines: int) -> list[str]:
    non_empty = [line for line in segment.lines if line.strip()]
    return non_empty[-max_lines:] if non_empty else []


def _is_structural_boilerplate(line: str) -> bool:
    """Detect generic boilerplate patterns without document-specific strings."""
    stripped = line.strip()
    if not stripped:
        return False
    if _PAGE_NUMBER_RE.match(stripped):
        return True
    if _CLASSIFICATION_RE.search(stripped):
        return True
    if _COPYRIGHT_RE.search(stripped):
        return True
    if _VERSION_RE.search(stripped) and len(stripped) < 120:
        return True
    return False


def _frequency_threshold(page_count: int, minimum: int, ratio: float) -> int:
    if page_count <= 1:
        return page_count + 1
    return max(minimum, int(page_count * ratio))


def remove_boilerplate(
    segments: list[PageSegment],
    settings: NormalizationSettings,
) -> CleaningStats:
    """Remove repeated headers and footers using cross-page frequency analysis."""
    stats = CleaningStats(pages_processed=len(segments))
    if not settings.enable_boilerplate_removal or len(segments) < 2:
        return stats

    page_count = len(segments)
    header_threshold = _frequency_threshold(
        page_count,
        settings.minimum_header_frequency,
        settings.boilerplate_min_page_ratio,
    )
    footer_threshold = _frequency_threshold(
        page_count,
        settings.minimum_footer_frequency,
        settings.boilerplate_min_page_ratio,
    )

    header_counter: Counter[str] = Counter()
    footer_counter: Counter[str] = Counter()

    for segment in segments:
        for line in _candidate_header_lines(segment, settings.maximum_header_lines):
            header_counter[boilerplate_line_key(line)] += 1
        for line in _candidate_footer_lines(segment, settings.maximum_footer_lines):
            footer_counter[boilerplate_line_key(line)] += 1

    header_boilerplate = {
        key
        for key, count in header_counter.items()
        if key and (count >= header_threshold or _is_structural_boilerplate_key(key))
    }
    footer_boilerplate = {
        key
        for key, count in footer_counter.items()
        if key and (count >= footer_threshold or _is_structural_boilerplate_key(key))
    }

    for segment in segments:
        cleaned: list[str] = []
        for index, line in enumerate(segment.lines):
            key = boilerplate_line_key(line)
            is_header_region = index < settings.maximum_header_lines
            is_footer_region = index >= max(0, len(segment.lines) - settings.maximum_footer_lines)

            if is_header_region and key in header_boilerplate:
                stats.headers_removed += 1
                stats.characters_removed += len(line)
                continue
            if is_footer_region and key in footer_boilerplate:
                stats.footers_removed += 1
                stats.characters_removed += len(line)
                continue
            if _is_structural_boilerplate(line):
                stats.footers_removed += 1
                stats.characters_removed += len(line)
                continue
            cleaned.append(line)
        segment.lines = cleaned

    return stats


def _is_structural_boilerplate_key(key: str) -> bool:
    return (
        bool(_PAGE_NUMBER_RE.match(key))
        or bool(_CLASSIFICATION_RE.search(key))
        or bool(_COPYRIGHT_RE.search(key))
    )
