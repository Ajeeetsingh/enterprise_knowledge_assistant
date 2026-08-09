"""Structural taxonomy hierarchy relationships."""

from __future__ import annotations

from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.discovery.helpers import make_relationship
from app.knowledge_relationships.enums import EvidenceSource, RelationshipType
from app.knowledge_relationships.types import (
    KnowledgeRelationshipRecord,
    RelationshipEvidenceItem,
)


class TaxonomyDiscoverer:
    name = "taxonomy"

    def discover(
        self,
        source: RegistryEntry,
        peers: list[RegistryEntry],
    ) -> list[KnowledgeRelationshipRecord]:
        results: list[KnowledgeRelationshipRecord] = []
        source_path = (source.taxonomy_path or "").strip("/")
        if not source_path:
            return results

        for peer in peers:
            if peer.knowledge_id == source.knowledge_id:
                continue
            peer_path = (peer.taxonomy_path or "").strip("/")
            if not peer_path or peer_path == source_path:
                continue

            if peer_path.startswith(source_path + "/"):
                parent = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.PARENT_OF.value,
                    confidence=0.8,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.TAXONOMY.value,
                            evidence=f"{source_path} parent_of {peer_path}",
                            weight=1.0,
                        )
                    ],
                    evidence_source=EvidenceSource.TAXONOMY.value,
                )
                contains = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.CONTAINS.value,
                    confidence=0.75,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.TAXONOMY.value,
                            evidence=f"{source_path} contains {peer_path}",
                            weight=0.9,
                        )
                    ],
                    evidence_source=EvidenceSource.TAXONOMY.value,
                )
                if parent:
                    results.append(parent)
                if contains:
                    results.append(contains)

            if source_path.startswith(peer_path + "/"):
                child = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.CHILD_OF.value,
                    confidence=0.8,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.TAXONOMY.value,
                            evidence=f"{source_path} child_of {peer_path}",
                            weight=1.0,
                        )
                    ],
                    evidence_source=EvidenceSource.TAXONOMY.value,
                )
                belongs = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.BELONGS_TO.value,
                    confidence=0.75,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.TAXONOMY.value,
                            evidence=f"{source_path} belongs_to {peer_path}",
                            weight=0.9,
                        )
                    ],
                    evidence_source=EvidenceSource.TAXONOMY.value,
                )
                if child:
                    results.append(child)
                if belongs:
                    results.append(belongs)
        return results
