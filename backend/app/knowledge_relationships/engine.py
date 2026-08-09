"""Relationship Engine orchestrator (Phase 13.3)."""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.discovery.organizational import OrganizationalDiscoverer
from app.knowledge_relationships.discovery.semantic import SemanticDiscoverer
from app.knowledge_relationships.discovery.taxonomy import TaxonomyDiscoverer
from app.knowledge_relationships.discovery.versioning import VersioningDiscoverer
from app.knowledge_relationships.enums import RelationshipType
from app.knowledge_relationships.types import KnowledgeRelationshipRecord
from app.knowledge_relationships.version import RELATIONSHIP_PIPELINE_VERSION

_VALID_TYPES = {item.value for item in RelationshipType}


class RelationshipEngine:
    """Discover relationships between Registry entries.

    Discoverers are pluggable — future LLM discoverers can be appended without redesign.
    """

    def __init__(self, discoverers: Sequence | None = None) -> None:
        self._discoverers = list(discoverers) if discoverers is not None else [
            OrganizationalDiscoverer(),
            TaxonomyDiscoverer(),
            VersioningDiscoverer(),
            SemanticDiscoverer(),
        ]

    @property
    def pipeline_version(self) -> str:
        return RELATIONSHIP_PIPELINE_VERSION

    def discover_for(
        self,
        source: RegistryEntry,
        peers: list[RegistryEntry],
    ) -> list[KnowledgeRelationshipRecord]:
        found: list[KnowledgeRelationshipRecord] = []
        for discoverer in self._discoverers:
            found.extend(discoverer.discover(source, peers))
        return self._dedupe(found)

    def discover_all(self, entries: list[RegistryEntry]) -> list[KnowledgeRelationshipRecord]:
        all_rels: list[KnowledgeRelationshipRecord] = []
        for entry in entries:
            peers = [peer for peer in entries if peer.knowledge_id != entry.knowledge_id]
            all_rels.extend(self.discover_for(entry, peers))
        return self._dedupe(all_rels)

    def _dedupe(
        self,
        relationships: list[KnowledgeRelationshipRecord],
    ) -> list[KnowledgeRelationshipRecord]:
        best: dict[tuple[str, str, str], KnowledgeRelationshipRecord] = {}
        for rel in relationships:
            if rel.relationship_type not in _VALID_TYPES:
                continue
            if rel.source_knowledge_id == rel.target_knowledge_id:
                continue
            key = (rel.source_knowledge_id, rel.target_knowledge_id, rel.relationship_type)
            current = best.get(key)
            if current is None or rel.confidence > current.confidence:
                best[key] = rel
        return list(best.values())
