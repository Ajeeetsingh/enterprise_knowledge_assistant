"""Canonical relationship domain types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RelationshipEvidenceItem:
    evidence_source: str
    evidence: str
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeRelationshipRecord:
    """Canonical in-memory relationship before persistence."""

    relationship_id: str
    source_knowledge_id: str
    target_knowledge_id: str
    relationship_type: str
    confidence: float
    confidence_kind: str = "heuristic_estimate"
    evidence: list[RelationshipEvidenceItem] = field(default_factory=list)
    evidence_source: str = "taxonomy"
    created_by: str = "relationship_engine"
    status: str = "active"
    pipeline_version: str = "13.3.0"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


@dataclass
class RelationshipStatistics:
    relationship_count: int = 0
    type_counts: dict[str, int] = field(default_factory=dict)
    evidence_source_counts: dict[str, int] = field(default_factory=dict)
    confidence_buckets: dict[str, int] = field(default_factory=dict)
    documents_with_relationships: int = 0
    documents_without_relationships: list[str] = field(default_factory=list)
    coverage: float = 0.0
    top_connected: list[dict[str, Any]] = field(default_factory=list)
    avg_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
