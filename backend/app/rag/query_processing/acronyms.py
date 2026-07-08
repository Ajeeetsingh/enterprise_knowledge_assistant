"""Acronym expansion rules."""

from __future__ import annotations

import re

from app.rag.query_processing.registry import QueryRulesRegistry


def _token_pattern(term: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(term)}\b", re.I)


def expand_acronyms(
    query: str,
    registry: QueryRulesRegistry,
) -> tuple[str, tuple[str, ...]]:
    """Append acronym expansions while preserving the original query text."""
    additions: list[str] = []
    applied: list[str] = []

    for acronym, expansions in registry.acronyms.items():
        if _token_pattern(acronym).search(query):
            applied.append(f"acronym:{acronym}")
            for expansion in expansions:
                if expansion.lower() not in query.lower():
                    additions.append(expansion)

    if not additions:
        return query, tuple(applied)

    expanded = f"{query} {' '.join(additions)}".strip()
    return expanded, tuple(applied)
