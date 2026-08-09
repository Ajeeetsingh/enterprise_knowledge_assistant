"""Organizational relationship discovery."""

from __future__ import annotations

from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.discovery.helpers import make_relationship
from app.knowledge_relationships.enums import EvidenceSource, RelationshipType
from app.knowledge_relationships.types import (
    KnowledgeRelationshipRecord,
    RelationshipEvidenceItem,
)


class OrganizationalDiscoverer:
    name = "organizational"

    def discover(
        self,
        source: RegistryEntry,
        peers: list[RegistryEntry],
    ) -> list[KnowledgeRelationshipRecord]:
        results: list[KnowledgeRelationshipRecord] = []
        source_collections = set(source.collections or [])
        for peer in peers:
            if peer.knowledge_id == source.knowledge_id:
                continue
            peer_collections = set(peer.collections or [])
            shared = source_collections & peer_collections
            if shared:
                rel = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.SAME_COLLECTION.value,
                    confidence=0.7 + min(0.2, 0.05 * len(shared)),
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.COLLECTION.value,
                            evidence=f"shared_collections={sorted(shared)}",
                            weight=1.0,
                        )
                    ],
                    evidence_source=EvidenceSource.COLLECTION.value,
                )
                if rel:
                    results.append(rel)
                # Department signal mirrors collection for Phase 13.3.
                dept = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.SAME_DEPARTMENT.value,
                    confidence=0.65,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.COLLECTION.value,
                            evidence=f"shared_department_collections={sorted(shared)}",
                            weight=0.9,
                        )
                    ],
                    evidence_source=EvidenceSource.COLLECTION.value,
                )
                if dept:
                    results.append(dept)

            if source.taxonomy_path and source.taxonomy_path == peer.taxonomy_path:
                rel = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.SAME_TAXONOMY.value,
                    confidence=0.82,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.TAXONOMY.value,
                            evidence=f"taxonomy_path={source.taxonomy_path}",
                            weight=1.0,
                        )
                    ],
                    evidence_source=EvidenceSource.TAXONOMY.value,
                )
                if rel:
                    results.append(rel)
        return results
