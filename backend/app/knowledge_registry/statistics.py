"""Aggregate registry statistics for validation / console."""

from __future__ import annotations

from collections import Counter

from app.knowledge_registry.aliases.catalog import CANONICAL_ALIASES
from app.knowledge_registry.types import RegistryEntry, RegistryStatistics


def build_statistics(entries: list[RegistryEntry]) -> RegistryStatistics:
    if not entries:
        return RegistryStatistics()

    collection_counts: Counter[str] = Counter()
    health_counts: Counter[str] = Counter()
    taxonomy_paths: set[str] = set()
    version_groups: set[str] = set()
    missing_collections: list[str] = []
    missing_categories: list[str] = []
    manual_review: list[str] = []
    duplicates = 0

    for entry in entries:
        for collection in entry.collections:
            collection_counts[collection] += 1
        health_counts[entry.health] += 1
        if entry.taxonomy_path:
            taxonomy_paths.add(entry.taxonomy_path)
        if entry.version_group_key:
            version_groups.add(entry.version_group_key)
        if entry.probable_duplicate_of:
            duplicates += 1
        if not entry.collections or entry.primary_collection == "unknown":
            missing_collections.append(entry.filename)
        if not entry.categories and not entry.taxonomy_path:
            missing_categories.append(entry.filename)
        if entry.needs_manual_review:
            manual_review.append(entry.filename)

    total = len(entries)
    with_collection = total - len(missing_collections)
    with_category = total - len(missing_categories)
    return RegistryStatistics(
        registered_count=total,
        collection_counts=dict(collection_counts),
        health_counts=dict(health_counts),
        taxonomy_paths=sorted(taxonomy_paths),
        alias_count=sum(len(v) for v in CANONICAL_ALIASES.values()),
        version_groups=len(version_groups),
        duplicate_candidates=duplicates,
        coverage_with_collection=round(with_collection / total, 3),
        coverage_with_category=round(with_category / total, 3),
        missing_collections=missing_collections,
        missing_categories=missing_categories,
        manual_review=manual_review,
    )
