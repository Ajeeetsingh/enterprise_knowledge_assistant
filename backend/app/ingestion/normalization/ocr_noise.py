"""Conservative OCR artefact cleanup."""

from __future__ import annotations

import re

from app.ingestion.normalization.types import CleaningStats

_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)", re.UNICODE)
_DUP_PUNCT_RE = re.compile(r"([!?.,;:])\1{2,}")
_GARBAGE_LINE_RE = re.compile(r"^[^\w\s]{1,2}$", re.UNICODE)


def clean_ocr_noise(text: str) -> tuple[str, CleaningStats]:
    """Apply conservative OCR cleanup without rewriting content."""
    stats = CleaningStats()
    original_len = len(text)

    def _replace_hyphen_break(match: re.Match[str]) -> str:
        stats.lines_normalized += 1
        return f"{match.group(1)}{match.group(2)}"

    text = _HYPHEN_BREAK_RE.sub(_replace_hyphen_break, text)

    def _collapse_punct(match: re.Match[str]) -> str:
        stats.lines_normalized += 1
        return match.group(1)

    text = _DUP_PUNCT_RE.sub(_collapse_punct, text)

    lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and _GARBAGE_LINE_RE.match(stripped):
            stats.characters_removed += len(line)
            continue
        lines.append(line)
    text = "\n".join(lines)

    stats.characters_removed += max(0, original_len - len(text))
    return text, stats
