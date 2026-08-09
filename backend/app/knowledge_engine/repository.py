"""Persistence for Knowledge Objects."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.db.models.document_knowledge import DocumentKnowledgeRecord
from app.knowledge_engine.types import DocumentKnowledge


class KnowledgeRepository:
    """CRUD helpers for ``document_knowledge`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(self, knowledge: DocumentKnowledge) -> DocumentKnowledgeRecord:
        document_id = uuid.UUID(str(knowledge.document_id))
        existing = (
            self._session.query(DocumentKnowledgeRecord)
            .filter(DocumentKnowledgeRecord.document_id == document_id)
            .one_or_none()
        )
        payload = knowledge.to_dict()
        fields = dict(
            knowledge_json=json.dumps(payload, ensure_ascii=True),
            document_type=knowledge.document_type,
            language=knowledge.language,
            short_summary=knowledge.summary.short,
            departments_json=json.dumps(knowledge.departments),
            topics_json=json.dumps(knowledge.topics),
            keywords_json=json.dumps(knowledge.keywords),
            tags_json=json.dumps(knowledge.tags),
            confidence_overall=float(knowledge.confidence.overall),
            pipeline_version=knowledge.processing_info.pipeline_version,
            model_used=knowledge.processing_info.model_used,
            processing_time_ms=float(knowledge.processing_info.processing_time_ms),
            status=knowledge.processing_info.status,
        )
        if existing is None:
            record = DocumentKnowledgeRecord(document_id=document_id, **fields)
            self._session.add(record)
        else:
            record = existing
            for key, value in fields.items():
                setattr(record, key, value)
        self._session.commit()
        self._session.refresh(record)
        return record

    def get_by_document_id(self, document_id: uuid.UUID | str) -> DocumentKnowledgeRecord | None:
        return (
            self._session.query(DocumentKnowledgeRecord)
            .filter(DocumentKnowledgeRecord.document_id == uuid.UUID(str(document_id)))
            .one_or_none()
        )

    def count(self) -> int:
        return self._session.query(DocumentKnowledgeRecord).count()

    def list_recent(self, *, limit: int = 50) -> list[DocumentKnowledgeRecord]:
        return (
            self._session.query(DocumentKnowledgeRecord)
            .order_by(DocumentKnowledgeRecord.updated_at.desc())
            .limit(limit)
            .all()
        )
