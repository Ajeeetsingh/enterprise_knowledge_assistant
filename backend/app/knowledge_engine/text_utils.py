"""Shared text helpers for Knowledge Engine analyzers."""

from __future__ import annotations

import re
from collections import Counter

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'_-]{1,}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_PAGE_MARKER_RE = re.compile(r"<<<PAGE:(\d+)>>>")

ENGLISH_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "by", "for", "from",
        "has", "have", "in", "is", "it", "its", "of", "on", "or", "that", "the",
        "their", "this", "to", "was", "were", "will", "with", "you", "your",
        "not", "can", "may", "must", "shall", "should", "all", "any", "each",
        "such", "than", "then", "into", "over", "under", "about", "after",
        "before", "between", "during", "through", "via", "also", "only",
        "other", "more", "most", "some", "these", "those", "when", "where",
        "which", "who", "whom", "what", "how", "why",
    }
)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()


def split_sentences(text: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []
    parts = _SENTENCE_RE.split(cleaned)
    return [part.strip() for part in parts if part.strip()]


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]


def significant_tokens(text: str, *, min_len: int = 3) -> list[str]:
    return [
        token
        for token in tokenize(text)
        if len(token) >= min_len and token not in ENGLISH_STOPWORDS
    ]


def top_keywords(text: str, *, limit: int = 15) -> list[str]:
    counts = Counter(significant_tokens(text))
    return [word for word, _ in counts.most_common(limit)]


def estimate_page_count(text: str) -> int:
    markers = [int(match.group(1)) for match in _PAGE_MARKER_RE.finditer(text)]
    if markers:
        return max(markers)
    # Rough estimate: ~500 words per page for plain text.
    words = len(tokenize(text))
    return max(1, (words + 499) // 500)


def detect_language(text: str) -> tuple[str, float]:
    """Lightweight English-vs-unknown detector (no external language libs)."""
    tokens = tokenize(text)
    if len(tokens) < 20:
        return "unknown", 0.35
    english_hits = sum(1 for token in tokens if token in ENGLISH_STOPWORDS)
    ratio = english_hits / len(tokens)
    if ratio >= 0.12:
        return "en", min(0.95, 0.55 + ratio)
    return "unknown", 0.4


def first_nonempty_lines(text: str, *, limit: int = 8) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or set(line) <= {"=", "-", "_", "*"}:
            continue
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines
