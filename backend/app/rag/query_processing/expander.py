"""Query expansion orchestration."""

from __future__ import annotations

import re

from app.rag.query_processing.acronyms import expand_acronyms
from app.rag.query_processing.config import QueryProcessingSettings
from app.rag.query_processing.entities import normalize_entities
from app.rag.query_processing.registry import QueryRulesRegistry
from app.rag.query_processing.schemas import ClassificationResult, QueryCategory
from app.rag.query_processing.synonyms import expand_synonyms


def _contains_any(query: str, terms: tuple[str, ...]) -> bool:
    lowered = query.lower()
    return any(term.lower() in lowered for term in terms)


def generate_retrieval_queries(
    *,
    original_query: str,
    normalized_query: str,
    expanded_query: str,
    classification: ClassificationResult,
    detected_entities: tuple[str, ...],
    registry: QueryRulesRegistry,
    settings: QueryProcessingSettings,
) -> tuple[str, ...]:
    """Build deduplicated retrieval queries for multi-query search."""
    queries: list[str] = [original_query]

    if settings.query_expansion_enabled and expanded_query.lower() != original_query.lower():
        queries.append(expanded_query)

    if normalized_query.lower() not in {item.lower() for item in queries}:
        queries.append(normalized_query)

    if settings.multi_query_enabled:
        lowered = original_query.lower()
        for trigger, variants in registry.multi_query_variants.items():
            if trigger in lowered or _contains_any(lowered, (trigger,)):
                for variant in variants:
                    queries.append(variant)

        if classification.category == QueryCategory.ENTITY_LOOKUP:
            if "headquarters" in lowered or "hq" in lowered:
                queries.extend(registry.multi_query_variants.get("headquarters", ()))
            if "ceo" in lowered or "chief executive" in lowered:
                queries.extend(registry.multi_query_variants.get("ceo", ()))

        if classification.category == QueryCategory.FINANCIAL:
            queries.extend(registry.multi_query_variants.get("revenue", ()))

        if classification.category == QueryCategory.POLICY:
            queries.extend(registry.multi_query_variants.get("policy", ()))

        if classification.category == QueryCategory.COMPLIANCE:
            queries.extend(registry.multi_query_variants.get("compliance", ()))

        if classification.category == QueryCategory.SECURITY:
            queries.extend(registry.multi_query_variants.get("security", ()))

        for entity_key in detected_entities:
            spec = registry.entities.get(entity_key)
            if spec is None:
                continue
            queries.append(f"What is {spec.canonical}?")
            if classification.category == QueryCategory.ENTITY_LOOKUP:
                queries.append(f"Who is {spec.canonical}?")

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = re.sub(r"\s+", " ", query.strip().lower())
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(query.strip())
        if len(deduped) >= settings.max_generated_queries:
            break

    return tuple(deduped or (original_query,))


def expand_query(
    query: str,
    *,
    registry: QueryRulesRegistry,
    settings: QueryProcessingSettings,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    """Normalize and expand a query using configured rules."""
    rules_applied: list[str] = []
    working = query.strip()

    normalized = working
    detected: tuple[str, ...] = ()
    if settings.entity_normalization_enabled:
        normalized, detected, entity_rules = normalize_entities(working, registry)
        rules_applied.extend(entity_rules)

    expanded = normalized
    if settings.query_expansion_enabled:
        expanded, acronym_rules = expand_acronyms(expanded, registry)
        rules_applied.extend(acronym_rules)

        if settings.synonym_expansion_enabled:
            expanded, synonym_rules = expand_synonyms(expanded, registry)
            rules_applied.extend(synonym_rules)

    return normalized, expanded, detected, tuple(rules_applied)
