"""Enterprise-aware retrieval query expansion from QueryUnderstanding.

Generates ranked semantic retrieval variants. The original user question is
always preserved separately for answer generation — these strings are only
used as retrieval inputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.query_processing.understanding import QueryUnderstanding

# Concept key → ranked retrieval variants (most specific first).
_CONCEPT_VARIANTS: dict[str, tuple[str, ...]] = {
    "mission": (
        "mission",
        "mission statement",
        "company mission",
        "corporate mission",
        "organization mission",
    ),
    "vision": (
        "vision",
        "company vision",
        "corporate vision",
        "organization vision",
    ),
    "core_values": (
        "core values",
        "company values",
        "corporate values",
        "organizational values",
        "ethical principles",
        "values",
    ),
    "metadata": (
        "metadata standard",
        "enterprise metadata",
        "metadata categories",
        "business metadata",
        "technical metadata",
        "metadata",
        "metadata taxonomy",
    ),
    "taxonomy": (
        "knowledge taxonomy",
        "enterprise knowledge taxonomy",
        "taxonomy hierarchy",
        "knowledge classification hierarchy",
        "taxonomy domains",
        "taxonomy",
    ),
    "approval": (
        "approval matrix",
        "approval authority",
        "approval workflow",
        "approval process",
        "approval policy",
        "authority matrix",
        "delegation of authority",
    ),
    "leave": (
        "leave encashment",
        "leave payout",
        "leave policy",
        "annual leave payout",
        "leave settlement",
        "encashment policy",
        "PTO encashment",
    ),
    "retention": (
        "records retention",
        "retention schedule",
        "retention policy",
        "document retention",
        "records retention schedule",
    ),
    "committee": (
        "committee governance",
        "committee charter",
        "governance structure",
        "board committees",
        "committee responsibilities",
    ),
    "business_process": (
        "business process classification",
        "process classification guide",
        "business process catalog",
        "process taxonomy",
        "business processes",
    ),
    "naming_versioning": (
        "document naming",
        "document versioning",
        "naming and versioning",
        "document naming standard",
        "version control policy",
    ),
    "company_profile": (
        "company profile",
        "organization profile",
        "master company profile",
    ),
}

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "for",
        "to",
        "in",
        "on",
        "is",
        "are",
        "what",
        "how",
        "when",
        "where",
        "who",
        "why",
        "explain",
        "describe",
        "define",
        "tell",
        "me",
        "about",
        "does",
        "do",
        "did",
        "with",
        "from",
        "this",
        "that",
        "our",
        "your",
        "their",
    }
)


@dataclass(frozen=True)
class ExpandedRetrievalQuery:
    """One ranked retrieval query candidate."""

    query: str
    confidence: float
    strategy: str


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _keyword_fragments(question: str) -> list[str]:
    """Extract distinctive multi-word / single-word fragments from the question."""
    tokens = [
        tok
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9'/&.-]{2,}", question)
        if tok.lower() not in _STOPWORDS
    ]
    fragments: list[str] = []
    # Prefer bigrams then unigrams.
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]} {tokens[i + 1]}"
        fragments.append(bigram)
    fragments.extend(tokens)
    return fragments


def expand_from_understanding(
    *,
    original_query: str,
    understanding: QueryUnderstanding,
    max_queries: int = 8,
) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    """Build ranked retrieval queries from understanding.

    Returns:
        (retrieval_queries, expansion_rules, strategy_label)
    """
    candidates: list[ExpandedRetrievalQuery] = []
    rules: list[str] = []

    # Always keep the original as the first retrieval query.
    candidates.append(
        ExpandedRetrievalQuery(original_query.strip(), confidence=1.0, strategy="original")
    )

    for concept in understanding.concepts:
        variants = _CONCEPT_VARIANTS.get(concept, ())
        if variants:
            rules.append(f"concept:{concept}")
        for index, variant in enumerate(variants):
            # Higher rank for earlier (more specific) variants.
            confidence = max(0.55, 0.92 - index * 0.04)
            candidates.append(
                ExpandedRetrievalQuery(
                    variant,
                    confidence=confidence,
                    strategy=f"concept:{concept}",
                )
            )

    for doc_hint in understanding.likely_documents:
        rules.append(f"likely_doc:{doc_hint}")
        # Pair document-type hints with primary concepts.
        for concept in understanding.concepts[:3]:
            label = concept.replace("_", " ")
            paired = f"{doc_hint} {label}".strip()
            candidates.append(
                ExpandedRetrievalQuery(
                    paired,
                    confidence=0.84,
                    strategy="likely_document_pair",
                )
            )
        candidates.append(
            ExpandedRetrievalQuery(
                doc_hint,
                confidence=0.78,
                strategy="likely_document",
            )
        )

    for entity in understanding.entities:
        # Skip very long entity spans as standalone retrieval queries.
        if len(entity.split()) > 6:
            continue
        rules.append(f"entity:{entity}")
        candidates.append(
            ExpandedRetrievalQuery(
                entity,
                confidence=0.8,
                strategy="entity",
            )
        )
        for concept in understanding.concepts[:2]:
            label = concept.replace("_", " ")
            candidates.append(
                ExpandedRetrievalQuery(
                    f"{entity} {label}",
                    confidence=0.77,
                    strategy="entity_concept",
                )
            )

    # Lightweight keyword fragments from the question (mission / vision style).
    for fragment in _keyword_fragments(original_query)[:10]:
        if _normalize_key(fragment) == _normalize_key(original_query):
            continue
        candidates.append(
            ExpandedRetrievalQuery(
                fragment,
                confidence=0.7,
                strategy="keyword_fragment",
            )
        )
        rules.append("keyword_fragments")

    # Deduplicate by normalized text, keep highest confidence, preserve original first.
    best: dict[str, ExpandedRetrievalQuery] = {}
    for item in candidates:
        key = _normalize_key(item.query)
        if not key:
            continue
        existing = best.get(key)
        if existing is None or item.confidence > existing.confidence:
            best[key] = item

    original_key = _normalize_key(original_query)
    ranked = sorted(
        best.values(),
        key=lambda item: (
            0 if _normalize_key(item.query) == original_key else 1,
            -item.confidence,
            item.query.lower(),
        ),
    )

    limit = max(1, min(max_queries, 12))
    selected = ranked[:limit]
    queries = tuple(item.query for item in selected)

    # Unique rules in stable order.
    seen_rules: set[str] = set()
    ordered_rules: list[str] = []
    for rule in rules:
        if rule not in seen_rules:
            seen_rules.add(rule)
            ordered_rules.append(rule)

    if understanding.concepts:
        strategy = "enterprise_concept_expansion"
    elif understanding.entities:
        strategy = "entity_expansion"
    else:
        strategy = "keyword_fragment_expansion"

    if "enterprise_understanding" not in ordered_rules:
        ordered_rules.insert(0, "enterprise_understanding")

    return queries, tuple(ordered_rules), strategy
