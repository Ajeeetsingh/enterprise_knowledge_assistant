"""Unicode normalization and invisible character cleanup."""

from __future__ import annotations

import re
import unicodedata

from app.ingestion.normalization.types import CleaningStats

_UNICODE_REPLACEMENTS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u00a0": " ",
    "\u202f": " ",
    "\u2007": " ",
    "\u2022": "-",
    "\u25cf": "-",
    "\u25aa": "-",
    "\u2043": "-",
}

_INVISIBLE_CHARS_RE = re.compile(
    r"[\u200b\u200c\u200d\u2060\ufeff\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)


def normalize_unicode(text: str) -> tuple[str, CleaningStats]:
    """Normalize unicode characters and remove invisible control characters."""
    stats = CleaningStats()
    original_len = len(text)

    text = unicodedata.normalize("NFKC", text)
    for source, target in _UNICODE_REPLACEMENTS.items():
        if source in text:
            text = text.replace(source, target)
            stats.lines_normalized += 1

    cleaned, removed = _INVISIBLE_CHARS_RE.subn("", text)
    if removed:
        stats.characters_removed += removed
        text = cleaned

    stats.characters_removed += max(0, original_len - len(text))
    return text, stats
