"""Heuristic multi-intent classifier."""

from __future__ import annotations

import re

from app.query_planner.enums import QueryIntent
from app.query_planner.models.types import IntentCandidate
from app.query_planner.parser.normalizer import NormalizationResult


_INTENT_PATTERNS: list[tuple[QueryIntent, tuple[str, ...], float, str]] = [
    (QueryIntent.COUNT_QUERY, (r"\bhow many\b", r"\bcount\b", r"\bnumber of\b"), 0.92, "count language"),
    (QueryIntent.COMPARISON, (r"\bcompare\b", r"\bdifference between\b", r"\bvs\.?\b", r"\bversus\b"), 0.9, "comparison language"),
    (QueryIntent.SUMMARY_REQUEST, (r"\bsummar(y|ize|ise)\b", r"\boverview\b", r"\btl;?dr\b"), 0.88, "summary language"),
    (QueryIntent.VERSION_LOOKUP, (r"\blatest\b", r"\boldest\b", r"\bversion\b", r"\bv\d+\b", r"\bfinal\b", r"\bprevious version\b"), 0.9, "version language"),
    (QueryIntent.RELATIONSHIP_QUERY, (r"\brelated to\b", r"\breferences?\b", r"\blinked to\b", r"\bdepends on\b", r"\brelationship\b"), 0.88, "relationship language"),
    (QueryIntent.NAVIGATION, (r"\bshow (me )?(all|the) (path|taxonomy|collection|category)\b", r"\bnavigate\b", r"\bbrowse\b", r"\bunder\b"), 0.75, "navigation language"),
    (QueryIntent.POLICY_LOOKUP, (r"\bpolicy\b", r"\bpolicies\b", r"\bhandbook\b"), 0.85, "policy language"),
    (QueryIntent.DEPARTMENT_SEARCH, (r"\bhr\b", r"\bfinance\b", r"\bsecurity\b", r"\bit\b", r"\blegal\b", r"\bdepartment\b"), 0.8, "department signal"),
    (QueryIntent.COLLECTION_SEARCH, (r"\bcollection\b", r"\bin finance\b", r"\bin hr\b", r"\bin security\b"), 0.78, "collection signal"),
    (QueryIntent.ENTITY_SEARCH, (r"\bmfa\b", r"\bvpn\b", r"\bemployee\b", r"\bcompany\b", r"\bincident\b", r"\bentity\b"), 0.78, "entity signal"),
    (QueryIntent.TOPIC_SEARCH, (r"\btopic\b", r"\babout\b", r"\bregarding\b"), 0.7, "topic signal"),
    (QueryIntent.KEYWORD_SEARCH, (r"\bkeyword\b", r"\bcontaining\b", r"\bmentions?\b"), 0.72, "keyword signal"),
    (QueryIntent.METADATA_SEARCH, (r"\bfilename\b", r"\buploaded\b", r"\bowner\b", r"\blanguage\b", r"\bextension\b", r"\bmetadata\b"), 0.86, "metadata signal"),
    (QueryIntent.DOCUMENT_LOOKUP, (r"\bfind (the )?document\b", r"\bget (the )?document\b", r"\bshow (me )?(the )?doc", r"\.pdf\b", r"\.docx?\b"), 0.8, "document lookup"),
]


class IntentClassifier:
    """Produce ranked intent candidates with heuristic confidence."""

    def classify(self, normalization: NormalizationResult) -> list[IntentCandidate]:
        text = f"{normalization.normalized} {normalization.original}".lower()
        scored: dict[str, IntentCandidate] = {}

        for intent, patterns, base, rationale in _INTENT_PATTERNS:
            hits = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))
            if not hits:
                continue
            confidence = min(0.99, base + 0.03 * (hits - 1))
            existing = scored.get(intent.value)
            if existing is None or confidence > existing.confidence:
                scored[intent.value] = IntentCandidate(
                    intent=intent.value,
                    confidence=round(confidence, 3),
                    rationale=rationale,
                )

        # Quoted phrases strongly suggest document/metadata lookup.
        if normalization.quoted_phrases:
            scored[QueryIntent.DOCUMENT_LOOKUP.value] = IntentCandidate(
                intent=QueryIntent.DOCUMENT_LOOKUP.value,
                confidence=0.91,
                rationale="quoted document/phrase",
            )

        if not scored:
            return [
                IntentCandidate(
                    intent=QueryIntent.UNKNOWN.value,
                    confidence=0.35,
                    rationale="no strong intent signals",
                )
            ]

        ranked = sorted(scored.values(), key=lambda item: item.confidence, reverse=True)
        # Soft boost KEYWORD_SEARCH as secondary when nothing else strong and query is short.
        if ranked[0].intent == QueryIntent.UNKNOWN.value and len(normalization.normalized.split()) >= 2:
            ranked.insert(
                0,
                IntentCandidate(
                    intent=QueryIntent.KEYWORD_SEARCH.value,
                    confidence=0.55,
                    rationale="fallback keyword search",
                ),
            )
        return ranked[:5]
