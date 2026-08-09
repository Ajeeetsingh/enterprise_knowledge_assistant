"""Shadow Mode wiring for the Knowledge Graph.

Builds the graph after Registry / Relationships / Hybrid Index artifacts are
available (document lifecycle). Optionally expands execution candidates in
Shadow Mode via GraphProvider. Never influences production answers.
Does not modify prior Phase 13 packages.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Callable

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
from app.knowledge_graph.providers.bridge import GraphAwareExecutionBridge
from app.knowledge_graph.providers.graph_provider import GraphProvider
from app.knowledge_graph.services.graph_service import KnowledgeGraphService
from app.knowledge_graph.storage.json_store import GraphJsonStore
from app.knowledge_graph.version import KNOWLEDGE_GRAPH_PIPELINE_VERSION
from app.knowledge_index.builders.document_builder import build_index_document
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_registry.repository import KnowledgeRegistryRepository
from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.repository import RelationshipRepository
from app.knowledge_relationships.types import (
    KnowledgeRelationshipRecord,
    RelationshipEvidenceItem,
)
from app.query_planner.services.planner_service import QueryPlannerService

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


class ShadowKnowledgeGraphService:
    """Build/update graph and optionally expand plans in Shadow Mode."""

    def __init__(
        self,
        *,
        graph_service: KnowledgeGraphService | None = None,
        session_factory: Callable[[], Session] | sessionmaker | None = None,
        enabled: bool | None = None,
    ) -> None:
        settings = get_settings()
        self._enabled = (
            settings.knowledge_graph_shadow_enabled if enabled is None else enabled
        )
        self._session_factory = session_factory or SessionLocal
        self._graph_service = graph_service or KnowledgeGraphService()
        self._store = GraphJsonStore(settings.indexes_path / "knowledge_graph")
        self._index_manager = KnowledgeIndexManager()
        self._planner = QueryPlannerService(index_manager=self._index_manager)
        self._bridge = GraphAwareExecutionBridge(
            graph_provider=GraphProvider(self._graph_service),
        )
        self._wrapped = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def graph_service(self) -> KnowledgeGraphService:
        return self._graph_service

    def on_lifecycle_event(self, event: DocumentLifecycleEvent) -> None:
        try:
            if not self._enabled:
                return
            if isinstance(event, (DocumentUploaded, DocumentRetryCompleted)):
                self.rebuild_from_persistence()
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge graph handler failed",
                document_id=getattr(event, "document_id", None),
                reason=type(exc).__name__,
            )

    def rebuild_from_persistence(self) -> int:
        if not self._enabled:
            return 0
        session = self._session_factory()
        try:
            registry_repo = KnowledgeRegistryRepository(session)
            entries = registry_repo.peers_as_entries()
            # Enrich duplicates from rows when peers omit them
            rows = registry_repo.list_entries(limit=2000)
            by_doc = {str(row.document_id): row for row in rows}
            enriched: list[RegistryEntry] = []
            for entry in entries:
                row = by_doc.get(entry.document_id)
                if row is not None:
                    enriched.append(_registry_row_to_entry(row))
                else:
                    enriched.append(entry)

            knowledge_rows = KnowledgeRepository(session).list_recent(limit=2000)
            knowledge_by_doc = {
                str(row.document_id): DocumentKnowledge.from_dict(json.loads(row.knowledge_json))
                for row in knowledge_rows
            }
            id_map = {entry.knowledge_id: entry.document_id for entry in enriched}
            index_docs = []
            for entry in enriched:
                knowledge = knowledge_by_doc.get(entry.document_id)
                if knowledge is None:
                    continue
                index_docs.append(
                    build_index_document(
                        knowledge=knowledge,
                        registry=entry,
                        relationships=[],
                        knowledge_id_to_document_id=id_map,
                    )
                )
            if index_docs:
                self._index_manager.build(index_docs)

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
            stats = self._graph_service.rebuild(
                registry_entries=enriched,
                relationships=relationships,
                index_documents=index_docs,
            )
            self._store.save(self._graph_service.graph, meta={"statistics": stats})
            log_with_fields(
                logger,
                logging.INFO,
                "Shadow knowledge graph rebuilt",
                node_count=stats.get("node_count"),
                edge_count=stats.get("edge_count"),
            )
            return int(stats.get("node_count") or 0)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge graph rebuild failed",
                reason=type(exc).__name__,
            )
            return 0
        finally:
            session.close()

    def analyze_query(self, query: str) -> None:
        """Plan + execute + optional graph expansion in Shadow Mode."""
        if not self._enabled or not query:
            return
        try:
            if not self._graph_service.available:
                # Best-effort rebuild; fail-open if empty.
                self.rebuild_from_persistence()
            plan = self._planner.plan(query, persist=False)
            self._bridge.execute(plan)
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Shadow knowledge graph query analysis failed",
                reason=type(exc).__name__,
            )

    def wrap_rag_service(self) -> None:
        if not self._enabled or self._wrapped:
            return
        try:
            from app.services.rag_service import get_rag_service

            rag = get_rag_service()
            original = rag.answer_question

            def _wrapped(
                question: str,
                role: str,
                authorized_sources: frozenset[str] | None = None,
                *,
                conversation_history: str | None = None,
            ) -> Any:
                try:
                    self.analyze_query(question)
                except Exception:  # noqa: BLE001
                    pass
                return original(
                    question,
                    role,
                    authorized_sources,
                    conversation_history=conversation_history,
                )

            rag.answer_question = _wrapped  # type: ignore[method-assign]
            self._wrapped = True
            log_with_fields(
                logger,
                logging.INFO,
                "Knowledge Graph shadow wrapper installed on RagService",
                pipeline_version=KNOWLEDGE_GRAPH_PIPELINE_VERSION,
            )
        except Exception as exc:  # noqa: BLE001
            log_with_fields(
                logger,
                logging.ERROR,
                "Knowledge Graph shadow wrap failed",
                reason=type(exc).__name__,
            )


@lru_cache
def get_shadow_knowledge_graph_service() -> ShadowKnowledgeGraphService:
    from app.services.document_service import get_document_service

    service = ShadowKnowledgeGraphService()
    if service.enabled:
        get_document_service().event_collector.subscribe(service.on_lifecycle_event)
        service.wrap_rag_service()
        log_with_fields(
            logger,
            logging.INFO,
            "Knowledge Graph shadow mode enabled",
            pipeline_version=KNOWLEDGE_GRAPH_PIPELINE_VERSION,
        )
    return service


def ensure_shadow_knowledge_graph_wired() -> None:
    get_shadow_knowledge_graph_service()
