"""Rule-based query intent detection for metadata-aware retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class QueryIntent(str, Enum):
    """Lightweight retrieval intent categories."""

    ENTITY_LOOKUP = "entity_lookup"
    SECTION_LOOKUP = "section_lookup"
    LIST_INTENT = "list_intent"
    TABLE_INTENT = "table_intent"
    NUMERIC_INTENT = "numeric_intent"
    GENERAL = "general"


_ENTITY_PATTERNS = (
    re.compile(r"^\s*what is\b", re.I),
    re.compile(r"^\s*who is\b", re.I),
    re.compile(r"^\s*where is\b", re.I),
    re.compile(r"^\s*what are\b", re.I),
    re.compile(r"\bheadquarters\b", re.I),
    re.compile(r"\blocated\b", re.I),
)

_SECTION_PATTERNS = (
    re.compile(r"\bsection\b", re.I),
    re.compile(r"\bchapter\b", re.I),
    re.compile(r"\bstrategic priorit", re.I),
    re.compile(r"\bpolicy\b", re.I),
    re.compile(r"\bappendix\b", re.I),
    re.compile(r"\boverview\b", re.I),
)

_LIST_PATTERNS = (
    re.compile(r"^\s*list\b", re.I),
    re.compile(r"\benumerate\b", re.I),
    re.compile(r"\bwhat are the\b", re.I),
    re.compile(r"\bwhich\b.+\bare\b", re.I),
)

_TABLE_PATTERNS = (
    re.compile(r"\btable\b", re.I),
    re.compile(r"\bmatrix\b", re.I),
    re.compile(r"\bbreakdown\b", re.I),
    re.compile(r"\bcomparison\b", re.I),
)

_NUMERIC_PATTERNS = (
    re.compile(r"\bhow many\b", re.I),
    re.compile(r"\bhow much\b", re.I),
    re.compile(r"\btotal\b", re.I),
    re.compile(r"\bcount\b", re.I),
    re.compile(r"\bpercentage\b", re.I),
    re.compile(r"\bpercent\b", re.I),
    re.compile(r"\brevenue\b", re.I),
    re.compile(r"\bbudget\b", re.I),
)


@dataclass(frozen=True)
class IntentDetectionResult:
    """Detected intent with optional secondary signals."""

    primary: QueryIntent
    signals: tuple[str, ...]


def detect_query_intent(query: str) -> IntentDetectionResult:
    """Detect retrieval intent using deterministic keyword rules."""
    normalized = query.strip()
    signals: list[str] = []

    if any(pattern.search(normalized) for pattern in _TABLE_PATTERNS):
        signals.append("table_keyword")
        return IntentDetectionResult(QueryIntent.TABLE_INTENT, tuple(signals))

    if any(pattern.search(normalized) for pattern in _NUMERIC_PATTERNS):
        signals.append("numeric_keyword")
        return IntentDetectionResult(QueryIntent.NUMERIC_INTENT, tuple(signals))

    if any(pattern.search(normalized) for pattern in _SECTION_PATTERNS):
        signals.append("section_keyword")
        return IntentDetectionResult(QueryIntent.SECTION_LOOKUP, tuple(signals))

    if any(pattern.search(normalized) for pattern in _LIST_PATTERNS):
        signals.append("list_keyword")
        return IntentDetectionResult(QueryIntent.LIST_INTENT, tuple(signals))

    if any(pattern.search(normalized) for pattern in _ENTITY_PATTERNS):
        signals.append("entity_keyword")
        return IntentDetectionResult(QueryIntent.ENTITY_LOOKUP, tuple(signals))

    return IntentDetectionResult(QueryIntent.GENERAL, tuple(signals))
