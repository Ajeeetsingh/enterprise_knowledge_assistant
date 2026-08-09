"""Shared helpers for relationship discovery."""

from __future__ import annotations

import uuid

from app.knowledge_relationships.enums import ConfidenceKind
from app.knowledge_relationships.types import (
    KnowledgeRelationshipRecord,
    RelationshipEvidenceItem,
)
from app.knowledge_relationships.version import RELATIONSHIP_PIPELINE_VERSION


def make_relationship(
    *,
    source_id: str,
    target_id: str,
    relationship_type: str,
    confidence: float,
    evidence: list[RelationshipEvidenceItem],
    evidence_source: str,
) -> KnowledgeRelationshipRecord | None:
    if not source_id or not target_id or source_id == target_id:
        return None
    conf = max(0.0, min(0.99, round(confidence, 3)))
    primary = evidence_source
    if evidence:
        primary = evidence[0].evidence_source
    return KnowledgeRelationshipRecord(
        relationship_id=str(uuid.uuid4()),
        source_knowledge_id=source_id,
        target_knowledge_id=target_id,
        relationship_type=relationship_type,
        confidence=conf,
        confidence_kind=ConfidenceKind.HEURISTIC_ESTIMATE.value,
        evidence=evidence,
        evidence_source=primary,
        created_by="relationship_engine",
        status="active",
        pipeline_version=RELATIONSHIP_PIPELINE_VERSION,
    )
