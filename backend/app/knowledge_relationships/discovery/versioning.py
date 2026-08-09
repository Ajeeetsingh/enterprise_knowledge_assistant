"""Versioning and duplicate relationship discovery."""

from __future__ import annotations

from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.discovery.helpers import make_relationship
from app.knowledge_relationships.enums import EvidenceSource, RelationshipType
from app.knowledge_relationships.types import (
    KnowledgeRelationshipRecord,
    RelationshipEvidenceItem,
)


class VersioningDiscoverer:
    name = "versioning"

    def discover(
        self,
        source: RegistryEntry,
        peers: list[RegistryEntry],
    ) -> list[KnowledgeRelationshipRecord]:
        results: list[KnowledgeRelationshipRecord] = []

        if source.probable_duplicate_of:
            dup = make_relationship(
                source_id=source.knowledge_id,
                target_id=source.probable_duplicate_of,
                relationship_type=RelationshipType.DUPLICATE_OF.value,
                confidence=max(0.72, min(0.95, source.duplicate_score or 0.85)),
                evidence=[
                    RelationshipEvidenceItem(
                        evidence_source=EvidenceSource.DUPLICATE_SIGNAL.value,
                        evidence=f"registry_duplicate_score={source.duplicate_score}",
                        weight=1.0,
                    )
                ],
                evidence_source=EvidenceSource.DUPLICATE_SIGNAL.value,
            )
            if dup:
                results.append(dup)

        if not source.version_group_key:
            return results

        group = [
            peer
            for peer in peers
            if peer.version_group_key == source.version_group_key
            and peer.knowledge_id != source.knowledge_id
        ]
        group_sorted = sorted(
            [source, *group],
            key=lambda item: (item.version_rank, item.filename),
        )
        ids = [item.knowledge_id for item in group_sorted]
        if source.knowledge_id not in ids:
            return results
        index = ids.index(source.knowledge_id)

        if index > 0:
            prev_id = ids[index - 1]
            prev = make_relationship(
                source_id=source.knowledge_id,
                target_id=prev_id,
                relationship_type=RelationshipType.PREVIOUS_VERSION.value,
                confidence=0.88,
                evidence=[
                    RelationshipEvidenceItem(
                        evidence_source=EvidenceSource.VERSION_GROUP.value,
                        evidence=f"version_group={source.version_group_key}; rank={source.version_rank}",
                        weight=1.0,
                    )
                ],
                evidence_source=EvidenceSource.VERSION_GROUP.value,
            )
            if prev:
                results.append(prev)

        if index < len(ids) - 1:
            next_id = ids[index + 1]
            nxt = make_relationship(
                source_id=source.knowledge_id,
                target_id=next_id,
                relationship_type=RelationshipType.NEXT_VERSION.value,
                confidence=0.88,
                evidence=[
                    RelationshipEvidenceItem(
                        evidence_source=EvidenceSource.VERSION_GROUP.value,
                        evidence=f"version_group={source.version_group_key}; rank={source.version_rank}",
                        weight=1.0,
                    )
                ],
                evidence_source=EvidenceSource.VERSION_GROUP.value,
            )
            if nxt:
                results.append(nxt)

            # Higher rank supersedes lower ranks in the same group.
            for older in group_sorted[:index]:
                supersedes = make_relationship(
                    source_id=source.knowledge_id,
                    target_id=older.knowledge_id,
                    relationship_type=RelationshipType.SUPERSEDES.value,
                    confidence=0.84,
                    evidence=[
                        RelationshipEvidenceItem(
                            evidence_source=EvidenceSource.VERSION_GROUP.value,
                            evidence=(
                                f"{source.version_label or source.version_rank} "
                                f"supersedes {older.version_label or older.version_rank}"
                            ),
                            weight=1.0,
                        )
                    ],
                    evidence_source=EvidenceSource.VERSION_GROUP.value,
                )
                if supersedes:
                    results.append(supersedes)

        return results
