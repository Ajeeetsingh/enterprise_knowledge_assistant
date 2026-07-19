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

# Short standalone lines that read as a heading purely by structure: no
# numbering, no ALL-CAPS, no keyword match, but also no mid-sentence
# punctuation — e.g. "Strategic priorities", "Risk governance", or
# interrogative FAQ-style headings such as "Who are the main issuers?".
# This is the fallback pattern (tried last) that lets short declarative or
# question headings be tagged as real headings instead of being silently
# absorbed into the following paragraph's body text.
_SHORT_HEADING_MAX_WORDS = 8

# Mirrors the bullet/ordered-list markers recognised by `structure.lists` so
# list items (which are also short, capitalized, and often unpunctuated)
# are never mistaken for the short-heading fallback below.
_LIST_MARKER_RE = re.compile(r"^(?:[-*\u2022\u25E6\u2023]\s+|\d+[.)]\s+|[a-zA-Z][.)]\s+)")

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


def _next_line_continues_sentence(next_text: str) -> bool:
    """Return True when *next_text* reads as a continuation of the previous line.

    A wrapped line break inside one sentence is, in English prose, almost
    always followed by a lowercase word (or a comma/connective) — a genuine
    new sentence or heading's body starts with an uppercase letter (or a
    digit/quote). This needs no keyword/topic knowledge, so it generalizes:
    it is what lets "Large corporations, financial institutions, and money
    market participants" (continues "...are the primary group...", lowercase
    "are") be rejected as a heading while "Strategic priorities" (followed by
    "The bank will focus...", uppercase "The") is correctly kept as one.
    """
    stripped = next_text.strip()
    first_alpha = next((char for char in stripped if char.isalpha()), "")
    return bool(first_alpha) and first_alpha.islower()


def _looks_like_short_standalone_heading(
    text: str,
    settings: StructureExtractionSettings,
    *,
    preceded_by_break: bool,
    next_text: str | None,
) -> bool:
    """Detect short declarative/interrogative headings with no other structural marker.

    Generic, non-keyword heuristic: a heading-shaped line is short, starts
    with a capital letter, and does **not** end with the kind of terminal
    punctuation ordinary prose sentences end with (a period or semicolon).
    A trailing "?" is allowed since many FAQ-style enterprise documents use
    interrogative section headings (e.g. "Who are the main issuers?").
    This intentionally does not reference any specific words/topics, so it
    generalizes across domains and document sets.

    ``preceded_by_break`` requires the candidate line to sit at a paragraph
    boundary (start of document/page or right after a blank line). Without
    this, a short *mid-paragraph* line — e.g. one half of a sentence that
    happens to wrap at a page-width boundary in PDF-extracted text, such as
    "Large corporations, financial institutions, and money market
    participants" — would otherwise be misread as a heading purely because
    it is short and its wrap point doesn't fall on terminal punctuation.
    Genuine standalone headings are always separated from surrounding prose
    by a paragraph break, so this keeps the heuristic safe for real,
    line-wrapped document text while still catching true short headings.

    ``next_text`` (the immediately following physical line, if any) is used
    for the same reason: see `_next_line_continues_sentence`.
    """
    if not preceded_by_break:
        return False
    if not _looks_like_heading_title(text, settings):
        return False
    if text.endswith((".", ";", ",")):
        return False
    if _LIST_MARKER_RE.match(text):
        return False
    if next_text is not None and _next_line_continues_sentence(next_text):
        return False
    words = text.rstrip(":").split()
    return 1 <= len(words) <= _SHORT_HEADING_MAX_WORDS


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
    blank_line_indexes = {line.index for line in lines if line.is_blank}
    # Page markers (``<<<PAGE:N>>>``) are consumed by the line parser and
    # never become entries in `lines`, so a content line whose predecessor
    # index is simply absent (start of document, or right after a page
    # marker/page break) is just as much a paragraph boundary as an
    # explicit blank line.
    present_indexes = {line.index for line in lines}
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

        previous_index = line.index - 1
        preceded_by_break = (
            previous_index not in present_indexes or previous_index in blank_line_indexes
        )
        next_text = (
            content_lines[index + 1].text.strip() if index + 1 < len(content_lines) else None
        )
        if detected is None and _looks_like_short_standalone_heading(
            text, settings, preceded_by_break=preceded_by_break, next_text=next_text
        ):
            detected = DetectedHeading(
                line_index=line.index,
                text=text.rstrip(":"),
                level=2,
                section_number=None,
                page=line.page,
            )

        if detected is not None:
            headings.append(detected)
        index += 1

    return filter_toc_duplicate_headings(headings)
