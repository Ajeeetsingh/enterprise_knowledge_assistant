"""ORM model for persisted Knowledge Objects (Phase 13.1)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentKnowledgeRecord(Base):
    """Shadow-mode persistence for ``DocumentKnowledge``.

    Stores the full canonical object as JSON plus denormalized columns for
    validation console queries. Does not alter the ``documents`` table.
    """

    __tablename__ = "document_knowledge"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    knowledge_json: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, default="Unknown", index=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    short_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    departments_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    topics_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    keywords_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    tags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    confidence_overall: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False, default="13.1.0")
    model_used: Mapped[str] = mapped_column(String(64), nullable=False, default="heuristic-v1")
    processing_time_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="success", index=True)
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

    def knowledge_dict(self) -> dict[str, Any]:
        try:
            data = json.loads(self.knowledge_json)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
