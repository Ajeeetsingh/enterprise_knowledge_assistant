"""Whitespace normalization while preserving paragraph boundaries."""

from __future__ import annotations

import re

from app.ingestion.normalization.page_segments import is_page_marker
from app.ingestion.normalization.types import CleaningStats

_MULTI_BLANK_RE = re.compile(r"\n{3,}")


def normalize_whitespace(text: str) -> tuple[str, CleaningStats]:
    """Collapse excess whitespace while preserving markers and paragraph breaks."""
    stats = CleaningStats()
    original_len = len(text)

    text = text.strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\t", " ")

    lines: list[str] = []
    for line in text.split("\n"):
        if is_page_marker(line.strip()):
            lines.append(line.strip())
        else:
            normalized = " ".join(line.split())
            if normalized != line:
                stats.lines_normalized += 1
            lines.append(normalized)

    text = "\n".join(lines)
    collapsed = _MULTI_BLANK_RE.sub("\n\n", text)
    if collapsed != text:
        stats.lines_normalized += 1
    text = collapsed

    stats.characters_removed = max(0, original_len - len(text))
    return text, stats
