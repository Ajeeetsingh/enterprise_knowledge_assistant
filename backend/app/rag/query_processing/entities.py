"""Enterprise entity normalization."""

from __future__ import annotations

import re

from app.rag.query_processing.registry import EntitySpec, QueryRulesRegistry


def _alias_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(alias)}\b", re.I)


def detect_entities(query: str, registry: QueryRulesRegistry) -> tuple[str, ...]:
    """Return canonical entity keys detected in the query."""
    detected: list[str] = []
    for key, spec in registry.entities.items():
        terms = (key, spec.canonical, *spec.aliases)
        if any(_alias_pattern(term).search(query) for term in terms):
            detected.append(key)
    return tuple(detected)


def normalize_entities(
    query: str,
    registry: QueryRulesRegistry,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Replace aliases with canonical entity forms."""
    normalized = query
    applied: list[str] = []
    detected = detect_entities(query, registry)

    for key in detected:
        spec = registry.entities[key]
        replacements = sorted(
            {key, *spec.aliases},
            key=len,
            reverse=True,
        )
        for alias in replacements:
            pattern = _alias_pattern(alias)
            if pattern.search(normalized):
                normalized = pattern.sub(spec.canonical, normalized)
                applied.append(f"entity:{alias}->{spec.canonical}")

    return normalized.strip(), tuple(detected), tuple(applied)
