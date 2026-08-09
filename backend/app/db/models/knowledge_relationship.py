"""ORM models for Phase 13.3 Knowledge Relationship Engine."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_knowledge_id",
            "target_knowledge_id",
            "relationship_type",
            name="uq_knowledge_relationship_edge",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_knowledge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_knowledge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="heuristic_estimate")
    evidence_source: Mapped[str] = mapped_column(String(64), nullable=False, default="taxonomy")
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="relationship_engine")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False, default="13.3.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class RelationshipEvidence(Base):
    __tablename__ = "relationship_evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    relationship_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_relationships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_source: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
