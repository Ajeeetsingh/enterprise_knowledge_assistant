"""Heading detection for enterprise documents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ingestion.structure.config import StructureExtractionSettings
from app.ingestion.structure.line_stream import AnnotatedLine

_NUMBERED_DOTTED_RE = re.compile(r"^(?P<num>\d+)\.\s+(?P<title>.+)$")
_NUMBERED_SUB_RE = re.compile(r"^(?P<num>\d+\.\d+(?:\.\d+)*)\s+(?P<title>.+)$")
_SECTION_HEADING_RE = re.compile(
    r"^(?:Section|Chapter|Appendix|Annex)\s+(?P<num>[\dIVXLC]+)\b[:\-\.]?\s*(?P<title>.*)$",
    re.IGNORECASE,
)
_ROMAN_HEADING_RE = re.compile(
    r"^(?P<num>[IVXLC]+)\.\s+(?P<title>.+)$",
)
_NUMBER_ONLY_RE = re.compile(r"^\d+(?:\.\d+)*\.?$")
_PAGE_NUMBER_LINE_RE = re.compile(r"^\d{1,3}$")

_ENTERPRISE_HEADING_KEYWORDS = frozenset(
    {
        "scope",
        "definitions",
        "policies",
        "responsibilities",
        "responsibility",
        "purpose",
        "overview",
        "introduction",
        "appendix",
        "appendices",
        "annex",
        "chapter",
        "glossary",
        "table of contents",
    }
)


@dataclass
class DetectedHeading:
    """A heading detected in the line stream."""

    line_index: int
    text: str
    level: int
    section_number: str | None
    page: int | None


def _is_all_caps_heading(text: str, settings: StructureExtractionSettings) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters or len(text) > settings.max_heading_length:
        return False
    upper_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    if upper_ratio < 0.85:
        return False
    words = text.split()
    return 1 <= len(words) <= 12


def _keyword_heading_level(text: str) -> int | None:
    normalized = text.strip().lower().rstrip(":")
    if normalized in _ENTERPRISE_HEADING_KEYWORDS:
        return 1
    for keyword in _ENTERPRISE_HEADING_KEYWORDS:
        if normalized.startswith(f"{keyword} "):
            return 2
    return None


def _heading_level_from_number(section_number: str) -> int:
    cleaned = section_number.rstrip(".")
    if not cleaned:
        return 1
    return cleaned.count(".") + 1


def _looks_like_heading_title(text: str, settings: StructureExtractionSettings) -> bool:
    if not text or len(text) > settings.max_heading_length:
        return False
    if text.lower().startswith("policy note:"):
        return False
    if text.endswith((".", ";")) and len(text.split()) > 8:
        return False
    if _PAGE_NUMBER_LINE_RE.match(text):
        return False
    first_alpha = next((char for char in text if char.isalpha()), "")
    if first_alpha and first_alpha.islower():
        return False
    return True


def filter_toc_duplicate_headings(headings: list[DetectedHeading]) -> list[DetectedHeading]:
    """Drop first occurrences of repeated headings that typically belong to a TOC."""
    grouped: dict[str, list[DetectedHeading]] = {}
    for heading in headings:
        grouped.setdefault(heading.text.strip().lower(), []).append(heading)

    filtered: list[DetectedHeading] = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda item: item.line_index)
        if len(ordered) == 1:
            filtered.append(ordered[0])
        else:
            filtered.extend(ordered[1:])
    return sorted(filtered, key=lambda item: item.line_index)


def detect_headings(
    lines: list[AnnotatedLine],
    settings: StructureExtractionSettings,
) -> list[DetectedHeading]:
    """Detect headings across the annotated line stream."""
    headings: list[DetectedHeading] = []
    content_lines = [line for line in lines if not line.is_blank]
    index = 0
    while index < len(content_lines):
        line = content_lines[index]
        text = line.text.strip()
        if not text:
            index += 1
            continue

        detected: DetectedHeading | None = None

        for pattern in (_SECTION_HEADING_RE, _ROMAN_HEADING_RE):
            match = pattern.match(text)
            if match and _looks_like_heading_title(match.group("title") or text, settings):
                section_number = match.group("num")
                title = (match.group("title") or text).strip()
                if pattern is _SECTION_HEADING_RE:
                    display = text
                else:
                    display = f"{section_number} {title}".strip() if title else section_number
                detected = DetectedHeading(
                    line_index=line.index,
                    text=display,
                    level=_heading_level_from_number(section_number),
                    section_number=section_number,
                    page=line.page,
                )

        if detected is None:
            for numbered_pattern in (_NUMBERED_DOTTED_RE, _NUMBERED_SUB_RE):
                match = numbered_pattern.match(text)
                if not match or not _looks_like_heading_title(match.group("title"), settings):
                    continue
                section_number = match.group("num")
                title = match.group("title").strip()
                if numbered_pattern is _NUMBERED_DOTTED_RE and index + 1 < len(content_lines):
                    next_text = content_lines[index + 1].text.strip()
                    if _PAGE_NUMBER_LINE_RE.match(next_text):
                        index += 2
                        continue
                detected = DetectedHeading(
                    line_index=line.index,
                    text=f"{section_number} {title}".strip(),
                    level=_heading_level_from_number(section_number),
                    section_number=section_number,
                    page=line.page,
                )
                break

        if detected is None and _NUMBER_ONLY_RE.match(text) and index + 1 < len(content_lines):
            next_line = content_lines[index + 1]
            next_text = next_line.text.strip()
            if _looks_like_heading_title(next_text, settings) and not _PAGE_NUMBER_LINE_RE.match(next_text):
                section_number = text.rstrip(".")
                if index + 2 < len(content_lines) and _PAGE_NUMBER_LINE_RE.match(
                    content_lines[index + 2].text.strip()
                ):
                    index += 3
                    continue
                detected = DetectedHeading(
                    line_index=line.index,
                    text=f"{section_number} {next_text}".strip(),
                    level=_heading_level_from_number(section_number),
                    section_number=section_number,
                    page=line.page,
                )
                index += 1

        if detected is None:
            keyword_level = _keyword_heading_level(text)
            if keyword_level is not None:
                detected = DetectedHeading(
                    line_index=line.index,
                    text=text.rstrip(":"),
                    level=keyword_level,
                    section_number=None,
                    page=line.page,
                )

        if detected is None and _is_all_caps_heading(text, settings):
            detected = DetectedHeading(
                line_index=line.index,
                text=text,
                level=1,
                section_number=None,
                page=line.page,
            )

        if detected is not None:
            headings.append(detected)
        index += 1

    return filter_toc_duplicate_headings(headings)
