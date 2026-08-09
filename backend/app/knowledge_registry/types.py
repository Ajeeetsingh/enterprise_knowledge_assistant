"""Domain types for the Knowledge Registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TaxonomyNode:
    path: str
    name: str
    collection: str
    parent_path: str | None = None
    depth: int = 0


@dataclass
class RegistryEntry:
    """Organized view of a registered Knowledge Object."""

    knowledge_id: str
    document_id: str
    filename: str
    collections: list[str] = field(default_factory=list)
    primary_collection: str = "unknown"
    taxonomy_path: str = ""
    categories: list[str] = field(default_factory=list)
    canonical_concepts: list[str] = field(default_factory=list)
    aliases_applied: list[dict[str, str]] = field(default_factory=list)
    version_group_key: str | None = None
    version_label: str | None = None
    version_rank: int = 1
    probable_duplicate_of: str | None = None
    duplicate_score: float = 0.0
    health: str = "Unknown"
    needs_manual_review: bool = False
    review_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegistryStatistics:
    registered_count: int = 0
    collection_counts: dict[str, int] = field(default_factory=dict)
    health_counts: dict[str, int] = field(default_factory=dict)
    taxonomy_paths: list[str] = field(default_factory=list)
    alias_count: int = 0
    version_groups: int = 0
    duplicate_candidates: int = 0
    coverage_with_collection: float = 0.0
    coverage_with_category: float = 0.0
    missing_collections: list[str] = field(default_factory=list)
    missing_categories: list[str] = field(default_factory=list)
    manual_review: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
