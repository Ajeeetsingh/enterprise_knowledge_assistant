"""Shadow Mode runner — parallel to legacy ingestion, fail-open always."""

from __future__ import annotations

import logging
import uuid
from functools import lru_cache
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.core.logging import get_logger, log_with_fields
from app.db.models.document import Document
from app.db.session import SessionLocal
from app.documents.events import (
    DocumentLifecycleEvent,
    DocumentRetryCompleted,
    DocumentUploaded,
)
from app.documents.status import DocumentStatus
from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.repository import KnowledgeRepository
from app.knowledge_engine.text_source import extract_text_from_bytes
from app.knowledge_engine.types import DocumentKnowledge, KnowledgeAnalysisRequest
from app.storage.interface import StorageAdapter
from app.storage.local import LocalStorage

logger = get_logger(__name__)


class ShadowKnowledgeService:
    """Generate and persist Knowledge Objects without affecting upload outcomes.

    Subscribes to lifecycle events. Handler methods never raise.
    """

    def __init__(
        self,
        *,
        engine: KnowledgeEngine | None = None,
        storage: StorageAdapter | None = None,
        session_factory: Callable[[], Session] | sessionmaker | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self._engine = engine or KnowledgeEngine()
        self._storage = storage or LocalStorage(base_path=settings.documents_path)
        self._session_factory = session_factory or SessionLocal
        self._enabled = (
            settings.knowledge_engine_shadow_enabled if enabled is None else enabled
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def on_lifecycle_event(self, event: DocumentLifecycleEvent) -> None:
        """Lifecycle subscriber entry point — must never raise."""
        try:
            if not self._enabled:
                return
            if isinstance(event, (DocumentUploaded, DocumentRetryCompleted)):
                self.process_document_id(event.document_id)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge handler failed",
                document_id=getattr(event, "document_id", None),
                reason=type(exc).__name__,
            )

    def process_document_id(self, document_id: str) -> DocumentKnowledge | None:
        """Load a persisted document, analyze it, and upsert the Knowledge Object."""
        if not self._enabled or not document_id:
            return None

        session = self._session_factory()
        try:
            document = (
                session.query(Document)
                .filter(Document.id == uuid.UUID(str(document_id)))
                .one_or_none()
            )
            if document is None:
                log_with_fields(
                    logger,
                    logging.WARNING,
                    "Shadow knowledge skipped — document missing",
                    document_id=document_id,
                )
                return None
            if document.status == DocumentStatus.DELETED.value:
                return None

            storage_path = document.storage_path
            if not storage_path or storage_path.startswith("pending/"):
                log_with_fields(
                    logger,
                    logging.WARNING,
                    "Shadow knowledge skipped — storage unavailable",
                    document_id=document_id,
                )
                return None

            content = self._storage.resolve(storage_path).read_bytes()
            text = extract_text_from_bytes(document.filename, content)
            upload_date = (
                document.uploaded_at.isoformat() if document.uploaded_at else None
            )
            request = KnowledgeAnalysisRequest(
                document_id=str(document.id),
                filename=document.filename,
                content_type=document.content_type,
                file_size=int(document.file_size),
                text=text,
                uploader=str(document.uploaded_by),
                owner=str(document.owner_id) if document.owner_id else str(document.uploaded_by),
                upload_date=upload_date,
                department_hint=document.department,
            )
            knowledge = self._engine.analyze(request)
            knowledge_record = KnowledgeRepository(session).upsert(knowledge)
            self._register_knowledge(session, knowledge, knowledge_record.id)
            log_with_fields(
                logger,
                logging.INFO,
                "Shadow knowledge object generated",
                document_id=document_id,
                document_type=knowledge.document_type,
                confidence=knowledge.confidence.overall,
                processing_time_ms=knowledge.processing_info.processing_time_ms,
                status=knowledge.processing_info.status,
            )
            return knowledge
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge processing failed",
                document_id=document_id,
                reason=type(exc).__name__,
            )
            return None
        finally:
            session.close()

    def analyze_text(self, request: KnowledgeAnalysisRequest) -> DocumentKnowledge:
        """Direct analysis helper for offline validation / tests."""
        return self._engine.analyze(request)

    def _register_knowledge(
        self,
        session,
        knowledge: DocumentKnowledge,
        document_knowledge_id,
    ) -> None:
        """Phase 13.2 — fail-open Registry registration (Shadow Mode)."""
        try:
            settings = get_settings()
            if not getattr(settings, "knowledge_registry_shadow_enabled", True):
                return
            from app.knowledge_registry.repository import KnowledgeRegistryRepository
            from app.knowledge_registry.service import KnowledgeRegistryService

            repo = KnowledgeRegistryRepository(session)
            repo.ensure_seed_data()
            service = KnowledgeRegistryService()
            peers = repo.peers_as_entries(exclude_document_id=knowledge.document_id)
            existing = repo.get_by_document_id(knowledge.document_id)
            knowledge_id = str(existing.id) if existing is not None else None
            entry = service.build_entry(
                knowledge,
                knowledge_id=knowledge_id,
                peers=peers,
            )
            repo.upsert_entry(entry, document_knowledge_id=document_knowledge_id)
            log_with_fields(
                logger,
                logging.INFO,
                "Shadow knowledge registry entry upserted",
                document_id=knowledge.document_id,
                knowledge_id=entry.knowledge_id,
                collection=entry.primary_collection,
                health=entry.health,
            )
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge registry registration failed",
                document_id=knowledge.document_id,
                reason=type(exc).__name__,
            )


@lru_cache
def get_shadow_knowledge_service() -> ShadowKnowledgeService:
    """Return the cached shadow service and subscribe to lifecycle events."""
    from app.services.document_service import get_document_service

    service = ShadowKnowledgeService()
    if service.enabled:
        get_document_service().event_collector.subscribe(service.on_lifecycle_event)
        log_with_fields(
            logger,
            logging.INFO,
            "Knowledge Engine shadow mode enabled",
            pipeline_version="13.1.0",
        )
    return service


def ensure_shadow_knowledge_wired() -> None:
    """Idempotent startup hook used by the application lifespan."""
    get_shadow_knowledge_service()
