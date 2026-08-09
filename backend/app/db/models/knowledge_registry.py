"""ORM models for Phase 13.2 Knowledge Registry (Shadow Mode)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeCollection(Base):
    __tablename__ = "knowledge_collections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KnowledgeCategory(Base):
    __tablename__ = "knowledge_categories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KnowledgeAlias(Base):
    __tablename__ = "knowledge_aliases"
    __table_args__ = (UniqueConstraint("normalized_alias", name="uq_knowledge_alias_normalized"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KnowledgeVersionGroup(Base):
    __tablename__ = "knowledge_version_groups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    canonical_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class KnowledgeRegistryEntry(Base):
    """Central registry row — stable knowledge_id for each Knowledge Object."""

    __tablename__ = "knowledge_registry"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    """Stable Knowledge ID."""

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    document_knowledge_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("document_knowledge.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    primary_collection: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown", index=True)
    collections_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    taxonomy_path: Mapped[str] = mapped_column(String(512), nullable=False, default="", index=True)
    categories_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    canonical_concepts_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    aliases_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    version_group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_version_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version_group_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    version_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_registry.id", ondelete="SET NULL"),
        nullable=True,
    )
    duplicate_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="Unknown", index=True)
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    registry_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False, default="13.2.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def registry_dict(self) -> dict[str, Any]:
        try:
            data = json.loads(self.registry_json)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
