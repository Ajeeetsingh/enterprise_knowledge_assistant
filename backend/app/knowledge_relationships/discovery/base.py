"""Discovery plugin contract — open for extension (future LLM discoverers)."""

from __future__ import annotations

from typing import Protocol

from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.types import KnowledgeRelationshipRecord


class RelationshipDiscoverer(Protocol):
    """Single-responsibility discoverer that emits candidate relationships."""

    name: str

    def discover(
        self,
        source: RegistryEntry,
        peers: list[RegistryEntry],
    ) -> list[KnowledgeRelationshipRecord]:
        ...
