"""Shadow Mode wiring for the Relationship Engine.

Independent of Knowledge Engine / Registry package internals.
Consumes persisted Registry entries only.
"""

from __future__ import annotations

import logging
import uuid
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
from app.knowledge_registry.repository import KnowledgeRegistryRepository
from app.knowledge_relationships.engine import RelationshipEngine
from app.knowledge_relationships.repository import RelationshipRepository

logger = get_logger(__name__)


class ShadowRelationshipService:
    """Discover and persist relationships after Registry registration.

    Fail-open. Never raises into lifecycle dispatch.
    """

    def __init__(
        self,
        *,
        engine: RelationshipEngine | None = None,
        session_factory: Callable[[], Session] | sessionmaker | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self._engine = engine or RelationshipEngine()
        self._session_factory = session_factory or SessionLocal
        self._enabled = (
            settings.knowledge_relationship_shadow_enabled
            if enabled is None
            else enabled
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

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
                "Shadow relationship handler failed",
                document_id=getattr(event, "document_id", None),
                reason=type(exc).__name__,
            )

    def process_document_id(self, document_id: str) -> int:
        if not self._enabled or not document_id:
            return 0
        session = self._session_factory()
        try:
            registry_repo = KnowledgeRegistryRepository(session)
            source_row = registry_repo.get_by_document_id(document_id)
            if source_row is None:
                # Registry may not be ready yet; fail-open.
                return 0
            peers = registry_repo.peers_as_entries()
            source_entries = [
                peer for peer in peers if peer.knowledge_id == str(source_row.id)
            ]
            if not source_entries:
                # Reconstruct from row if peer list excludes self.
                from app.knowledge_registry.types import RegistryEntry
                import json

                source = RegistryEntry(
                    knowledge_id=str(source_row.id),
                    document_id=str(source_row.document_id),
                    filename=source_row.filename,
                    collections=json.loads(source_row.collections_json or "[]"),
                    primary_collection=source_row.primary_collection,
                    taxonomy_path=source_row.taxonomy_path,
                    categories=json.loads(source_row.categories_json or "[]"),
                    canonical_concepts=json.loads(source_row.canonical_concepts_json or "[]"),
                    version_group_key=source_row.version_group_key,
                    version_label=source_row.version_label,
                    version_rank=source_row.version_rank,
                    probable_duplicate_of=(
                        str(source_row.duplicate_of_id) if source_row.duplicate_of_id else None
                    ),
                    duplicate_score=float(source_row.duplicate_score or 0.0),
                    health=source_row.health_status,
                )
            else:
                source = source_entries[0]

            other_peers = [peer for peer in peers if peer.knowledge_id != source.knowledge_id]
            relationships = self._engine.discover_for(source, other_peers)
            # Keep only edges whose targets exist in registry.
            valid_targets = {peer.knowledge_id for peer in other_peers}
            relationships = [
                rel
                for rel in relationships
                if rel.target_knowledge_id in valid_targets
                or rel.relationship_type == "duplicate_of"
            ]
            # Validate target UUIDs exist for duplicate_of pointing at registry ids.
            filtered = []
            for rel in relationships:
                try:
                    uuid.UUID(str(rel.target_knowledge_id))
                except ValueError:
                    continue
                filtered.append(rel)

            RelationshipRepository(session).replace_for_source(source.knowledge_id, filtered)
            log_with_fields(
                logger,
                logging.INFO,
                "Shadow relationships persisted",
                document_id=document_id,
                knowledge_id=source.knowledge_id,
                relationship_count=len(filtered),
            )
            return len(filtered)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow relationship processing failed",
                document_id=document_id,
                reason=type(exc).__name__,
            )
            return 0
        finally:
            session.close()


@lru_cache
def get_shadow_relationship_service() -> ShadowRelationshipService:
    from app.services.document_service import get_document_service

    service = ShadowRelationshipService()
    if service.enabled:
        get_document_service().event_collector.subscribe(service.on_lifecycle_event)
        log_with_fields(
            logger,
            logging.INFO,
            "Knowledge Relationship Engine shadow mode enabled",
            pipeline_version="13.3.0",
        )
    return service


def ensure_shadow_relationships_wired() -> None:
    get_shadow_relationship_service()
