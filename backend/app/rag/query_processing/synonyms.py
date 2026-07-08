"""Synonym expansion rules."""

from __future__ import annotations

import re

from app.rag.query_processing.registry import QueryRulesRegistry


def _contains_term(query: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", query, re.I) is not None


def expand_synonyms(
    query: str,
    registry: QueryRulesRegistry,
) -> tuple[str, tuple[str, ...]]:
    """Append synonym terms found in the query."""
    additions: list[str] = []
    applied: list[str] = []

    for anchor, synonyms in registry.synonyms.items():
        if _contains_term(query, anchor):
            applied.append(f"synonym:{anchor}")
            for synonym in synonyms:
                if not _contains_term(query, synonym):
                    additions.append(synonym)
            continue

        for synonym in synonyms:
            if _contains_term(query, synonym):
                applied.append(f"synonym:{synonym}->{anchor}")
                if not _contains_term(query, anchor):
                    additions.append(anchor)
                break

    if not additions:
        return query, tuple(applied)

    expanded = f"{query} {' '.join(additions)}".strip()
    return expanded, tuple(applied)
