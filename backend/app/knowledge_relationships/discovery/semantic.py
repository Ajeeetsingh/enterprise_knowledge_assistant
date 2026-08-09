"""Semantic / cross-domain relationship discovery from registry concepts."""

from __future__ import annotations

from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.discovery.helpers import make_relationship
from app.knowledge_relationships.enums import EvidenceSource, RelationshipType
from app.knowledge_relationships.types import (
    KnowledgeRelationshipRecord,
    RelationshipEvidenceItem,
)


class SemanticDiscoverer:
    name = "semantic"

    def discover(
        self,
        source: RegistryEntry,
        peers: list[RegistryEntry],
    ) -> list[KnowledgeRelationshipRecord]:
        results: list[KnowledgeRelationshipRecord] = []
        source_concepts = {item.lower(): item for item in (source.canonical_concepts or [])}
        if not source_concepts:
            return results

        for peer in peers:
            if peer.knowledge_id == source.knowledge_id:
                continue
            peer_concepts = {item.lower(): item for item in (peer.canonical_concepts or [])}
            shared_keys = sorted(set(source_concepts) & set(peer_concepts))
            if not shared_keys:
                continue
            shared_labels = [source_concepts[key] for key in shared_keys]
            evidence = [
                RelationshipEvidenceItem(
                    evidence_source=EvidenceSource.CANONICAL_CONCEPT.value,
                    evidence=f"shared_concepts={shared_labels}",
                    weight=min(1.0, 0.4 + 0.2 * len(shared_labels)),
                )
            ]

            if len(shared_labels) >= 2:
                related = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.RELATED_TO.value,
                    confidence=0.7 + min(0.2, 0.05 * len(shared_labels)),
                    evidence=evidence,
                    evidence_source=EvidenceSource.CANONICAL_CONCEPT.value,
                )
                if related:
                    results.append(related)

            mentions = make_relationship(
                source_id=source.knowledge_id,
                target_id=peer.knowledge_id,
                relationship_type=RelationshipType.MENTIONS.value,
                confidence=0.6 + min(0.25, 0.05 * len(shared_labels)),
                evidence=evidence,
                evidence_source=EvidenceSource.CANONICAL_CONCEPT.value,
            )
            if mentions:
                results.append(mentions)

            references = make_relationship(
                source_id=source.knowledge_id,
                target_id=peer.knowledge_id,
                relationship_type=RelationshipType.REFERENCES.value,
                confidence=0.62 + min(0.2, 0.04 * len(shared_labels)),
                evidence=evidence,
                evidence_source=EvidenceSource.CANONICAL_CONCEPT.value,
            )
            if references:
                results.append(references)

            # Lightweight cross-domain heuristics from collection pairs.
            src = source.primary_collection
            tgt = peer.primary_collection
            if src == "security" and tgt != "security":
                governs = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.GOVERNS.value,
                    confidence=0.58,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.COLLECTION.value,
                            evidence=f"security_collection_governs_{tgt}",
                            weight=0.7,
                        ),
                        *evidence,
                    ],
                    evidence_source=EvidenceSource.COLLECTION.value,
                )
                if governs:
                    results.append(governs)
            if src == "hr" and tgt == "security":
                requires = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.REQUIRES.value,
                    confidence=0.55,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.COLLECTION.value,
                            evidence="hr_policy_may_require_security_controls",
                            weight=0.6,
                        )
                    ],
                    evidence_source=EvidenceSource.COLLECTION.value,
                )
                if requires:
                    results.append(requires)

            # Handbook/policy style: treat handbooks as explaining policies in same collection.
            if "handbook" in source.filename.lower() and "policy" in peer.filename.lower():
                if src == tgt:
                    explains = make_relationship(
                        source_id=source.knowledge_id,
                        target_id=peer.knowledge_id,
                        relationship_type=RelationshipType.EXPLAINS.value,
                        confidence=0.66,
                        evidence=[
                            RelationshipEvidenceItem(
                                evidence_source=EvidenceSource.DOCUMENT_TYPE.value,
                                evidence="handbook_explains_policy",
                                weight=0.8,
                            )
                        ],
                        evidence_source=EvidenceSource.DOCUMENT_TYPE.value,
                    )
                    if explains:
                        results.append(explains)

            if source.version_group_key and source.version_group_key == peer.version_group_key:
                extends = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=peer.knowledge_id,
                    relationship_type=RelationshipType.EXTENDS.value,
                    confidence=0.7,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.VERSION_GROUP.value,
                            evidence="same_version_family_extends",
                            weight=0.75,
                        )
                    ],
                    evidence_source=EvidenceSource.VERSION_GROUP.value,
                )
                if extends:
                    results.append(extends)

        return results
