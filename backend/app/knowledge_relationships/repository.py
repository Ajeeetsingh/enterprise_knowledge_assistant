"""Persistence for discovered relationships."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.knowledge_relationship import KnowledgeRelationship, RelationshipEvidence
from app.knowledge_relationships.types import KnowledgeRelationshipRecord


class RelationshipRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def replace_for_source(
        self,
        source_knowledge_id: str,
        relationships: list[KnowledgeRelationshipRecord],
    ) -> list[KnowledgeRelationship]:
        """Replace outbound relationships for a source knowledge id."""
        source_id = uuid.UUID(str(source_knowledge_id))
        existing = (
            self._session.query(KnowledgeRelationship)
            .filter(KnowledgeRelationship.source_knowledge_id == source_id)
            .all()
        )
        for row in existing:
            self._session.delete(row)
        self._session.flush()

        saved: list[KnowledgeRelationship] = []
        for rel in relationships:
            if str(rel.source_knowledge_id) != str(source_knowledge_id):
                continue
            try:
                target_id = uuid.UUID(str(rel.target_knowledge_id))
            except ValueError:
                continue
            row = KnowledgeRelationship(
                id=uuid.UUID(str(rel.relationship_id)),
                source_knowledge_id=source_id,
                target_knowledge_id=target_id,
                relationship_type=rel.relationship_type,
                confidence=float(rel.confidence),
                confidence_kind=rel.confidence_kind,
                evidence_source=rel.evidence_source,
                evidence_summary="; ".join(item.evidence for item in rel.evidence)[:2000],
                created_by=rel.created_by,
                status=rel.status,
                pipeline_version=rel.pipeline_version,
            )
            self._session.add(row)
            self._session.flush()
            for item in rel.evidence:
                self._session.add(
                    RelationshipEvidence(
                        relationship_id=row.id,
                        evidence_source=item.evidence_source,
                        evidence=item.evidence,
                        weight=float(item.weight),
                    )
                )
            saved.append(row)
        self._session.commit()
        return saved

    def count(self) -> int:
        return self._session.query(KnowledgeRelationship).count()

    def list_recent(self, *, limit: int = 500) -> list[KnowledgeRelationship]:
        return (
            self._session.query(KnowledgeRelationship)
            .order_by(KnowledgeRelationship.created_at.desc())
            .limit(limit)
            .all()
        )
