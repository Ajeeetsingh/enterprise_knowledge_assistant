"""Knowledge Relationship Engine (Phase 13.3) — Shadow Mode."""

from app.knowledge_relationships.engine import RelationshipEngine
from app.knowledge_relationships.types import KnowledgeRelationshipRecord, RelationshipStatistics
from app.knowledge_relationships.version import RELATIONSHIP_PIPELINE_VERSION

__all__ = [
    "RelationshipEngine",
    "KnowledgeRelationshipRecord",
    "RelationshipStatistics",
    "RELATIONSHIP_PIPELINE_VERSION",
]
