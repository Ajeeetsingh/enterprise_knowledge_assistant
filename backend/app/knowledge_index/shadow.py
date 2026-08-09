"""Shadow Mode wiring for the Hybrid Knowledge Index.

Independent of Knowledge Engine / Registry / Relationship packages internals.
Consumes persisted DocumentKnowledge, Registry entries, and Relationships.
Fail-open: never raises into lifecycle dispatch / never fails uploads.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.core.logging import get_logger, log_with_fields
from app.db.session import SessionLocal
from app.documents.events import (
    DocumentLifecycleEvent,
    DocumentRetryCompleted,
    DocumentUploaded,
)
from app.knowledge_engine.repository import KnowledgeRepository
from app.knowledge_engine.types import DocumentKnowledge
from app.knowledge_index.builders.document_builder import build_index_document
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_index.version import KNOWLEDGE_INDEX_PIPELINE_VERSION
from app.knowledge_registry.repository import KnowledgeRegistryRepository
from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.repository import RelationshipRepository

logger = get_logger(__name__)


def _registry_row_to_entry(row) -> RegistryEntry:
    return RegistryEntry(
        knowledge_id=str(row.id),
        document_id=str(row.document_id),
        filename=row.filename,
        collections=json.loads(row.collections_json or "[]"),
        primary_collection=row.primary_collection,
        taxonomy_path=row.taxonomy_path,
        categories=json.loads(row.categories_json or "[]"),
        canonical_concepts=json.loads(row.canonical_concepts_json or "[]"),
        version_group_key=row.version_group_key,
        version_label=row.version_label,
        version_rank=row.version_rank,
        probable_duplicate_of=(
            str(row.duplicate_of_id) if getattr(row, "duplicate_of_id", None) else None
        ),
        duplicate_score=float(getattr(row, "duplicate_score", 0.0) or 0.0),
        health=row.health_status,
    )


class ShadowKnowledgeIndexService:
    """Incrementally update Hybrid Knowledge Indexes after relationships.

    Fail-open. Never raises into lifecycle dispatch.
    """

    def __init__(
        self,
        *,
        manager: KnowledgeIndexManager | None = None,
        session_factory: Callable[[], Session] | sessionmaker | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self._session_factory = session_factory or SessionLocal
        self._enabled = (
            settings.knowledge_index_shadow_enabled if enabled is None else enabled
        )
        if manager is not None:
            self._manager = manager
        else:
            self._manager = KnowledgeIndexManager.with_default_store(settings.indexes_path)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def manager(self) -> KnowledgeIndexManager:
        return self._manager

    def on_lifecycle_event(self, event: DocumentLifecycleEvent) -> None:
        try:
            if not self._enabled:
                return
            if isinstance(event, (DocumentUploaded, DocumentRetryCompleted)):
                self.process_document_id(event.document_id)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge index handler failed",
                document_id=getattr(event, "document_id", None),
                reason=type(exc).__name__,
            )

    def process_document_id(self, document_id: str) -> bool:
        if not self._enabled or not document_id:
            return False
        session = self._session_factory()
        try:
            knowledge_row = KnowledgeRepository(session).get_by_document_id(document_id)
            if knowledge_row is None:
                return False
            knowledge = DocumentKnowledge.from_dict(json.loads(knowledge_row.knowledge_json))

            registry_repo = KnowledgeRegistryRepository(session)
            registry_row = registry_repo.get_by_document_id(document_id)
            registry = _registry_row_to_entry(registry_row) if registry_row else None

            peers = registry_repo.peers_as_entries()
            id_map = {peer.knowledge_id: peer.document_id for peer in peers}
            if registry:
                id_map[registry.knowledge_id] = registry.document_id

            relationships = []
            if registry:
                # Index edges where this knowledge id is the source.
                from app.knowledge_relationships.types import (
                    KnowledgeRelationshipRecord,
                    RelationshipEvidenceItem,
                )

                for row in RelationshipRepository(session).list_recent(limit=2000):
                    if str(row.source_knowledge_id) != registry.knowledge_id:
                        continue
                    relationships.append(
                        KnowledgeRelationshipRecord(
                            relationship_id=str(row.id),
                            source_knowledge_id=str(row.source_knowledge_id),
                            target_knowledge_id=str(row.target_knowledge_id),
                            relationship_type=row.relationship_type,
                            confidence=float(row.confidence or 0.0),
                            confidence_kind=row.confidence_kind or "heuristic_estimate",
                            evidence=[
                                RelationshipEvidenceItem(
                                    evidence_source=row.evidence_source or "unknown",
                                    evidence=row.evidence_summary or "",
                                )
                            ],
                            evidence_source=row.evidence_source or "unknown",
                            pipeline_version=row.pipeline_version or "13.3.0",
                        )
                    )

            document = build_index_document(
                knowledge=knowledge,
                registry=registry,
                relationships=relationships,
                knowledge_id_to_document_id=id_map,
            )
            self._manager.update(document)
            # Persist snapshot after incremental update.
            self._manager._persist()  # noqa: SLF001 — intentional shadow persist
            log_with_fields(
                logger,
                logging.INFO,
                "Shadow knowledge indexes updated",
                document_id=document_id,
                knowledge_id=document.knowledge_id,
                index_count=len(self._manager.indexes),
            )
            return True
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge index processing failed",
                document_id=document_id,
                reason=type(exc).__name__,
            )
            return False
        finally:
            session.close()

    def rebuild_all(self) -> int:
        """Full rebuild from persisted KO + Registry + Relationships (fail-open)."""
        if not self._enabled:
            return 0
        session = self._session_factory()
        try:
            from app.knowledge_index.builders.document_builder import build_index_documents
            from app.knowledge_relationships.types import (
                KnowledgeRelationshipRecord,
                RelationshipEvidenceItem,
            )

            knowledge_rows = KnowledgeRepository(session).list_recent(limit=5000)
            knowledge_objects = [
                DocumentKnowledge.from_dict(json.loads(row.knowledge_json))
                for row in knowledge_rows
            ]
            registry_entries = KnowledgeRegistryRepository(session).peers_as_entries()
            # peers_as_entries may omit duplicates of_id; enrich from rows when needed
            relationships = []
            for row in RelationshipRepository(session).list_recent(limit=10000):
                relationships.append(
                    KnowledgeRelationshipRecord(
                        relationship_id=str(row.id),
                        source_knowledge_id=str(row.source_knowledge_id),
                        target_knowledge_id=str(row.target_knowledge_id),
                        relationship_type=row.relationship_type,
                        confidence=float(row.confidence or 0.0),
                        evidence=[
                            RelationshipEvidenceItem(
                                evidence_source=row.evidence_source or "unknown",
                                evidence=row.evidence_summary or "",
                            )
                        ],
                        evidence_source=row.evidence_source or "unknown",
                    )
                )
            documents = build_index_documents(
                knowledge_objects=knowledge_objects,
                registry_entries=registry_entries,
                relationships=relationships,
            )
            self._manager.build(documents)
            return len(documents)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge index rebuild failed",
                reason=type(exc).__name__,
            )
            return 0
        finally:
            session.close()


@lru_cache
def get_shadow_knowledge_index_service() -> ShadowKnowledgeIndexService:
    from app.services.document_service import get_document_service

    service = ShadowKnowledgeIndexService()
    if service.enabled:
        get_document_service().event_collector.subscribe(service.on_lifecycle_event)
        log_with_fields(
            logger,
            logging.INFO,
            "Hybrid Knowledge Index shadow mode enabled",
            pipeline_version=KNOWLEDGE_INDEX_PIPELINE_VERSION,
        )
    return service


def ensure_shadow_knowledge_index_wired() -> None:
    get_shadow_knowledge_index_service()
