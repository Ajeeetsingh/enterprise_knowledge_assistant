"""Document management business logic."""

from __future__ import annotations

import logging
import time
import uuid
from functools import lru_cache

from app.config import get_settings
from sqlalchemy.exc import IntegrityError

from app.auth.document_authorization import DocumentAuthorizationService
from app.core.exceptions import (
    DocumentIngestionError,
    DocumentIntegrityError,
    DocumentNotFoundError,
    DocumentStorageError,
    DocumentValidationError,
    DuplicateDocumentError,
    EmbeddingError,
    StorageError,
)
from app.core.logging import get_logger, log_with_fields
from app.db.models.document import Document
from app.db.models.user import User
from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository
from app.documents.checksum import ChecksumProvider, Sha256ChecksumProvider
from app.documents.dispatcher import LifecycleEventCollector, get_lifecycle_event_collector
from app.documents.events import (
    DocumentDeleted,
    DocumentIndexed,
    DocumentProcessingCompleted,
    DocumentProcessingFailed,
    DocumentProcessingStarted,
    DocumentUploaded,
    DuplicateDetected,
)
from app.documents.integrity import (
    DuplicateDetectionPolicy,
    IntegrityDecision,
)
from app.documents.lifecycle import DocumentLifecycleResult
from app.documents.metrics import ProcessingMetrics
from app.documents.processing import DocumentProcessingOutcome
from app.documents.progress import ProcessingProgress
from app.documents.replacement import (
    DocumentReplacementHandler,
    UnimplementedReplacementHandler,
)
from app.documents.retry import (
    DefaultDocumentRetryHandler,
    DocumentRetryHandler,
    DocumentRetryResult,
)
from app.documents.status import DocumentStatus, DocumentUploadResult
from app.documents.types import IngestionContext, IngestionResult
from app.documents.versioning import DocumentVersionInfo
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import IngestionPipelineBase, create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.vector_store.base import VectorStore
from app.services.document_diagnostics_service import DocumentDiagnosticsService
from app.storage.interface import StorageAdapter
from app.storage.local import LocalStorage

DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 100

logger = get_logger(__name__)


def _failure_status_for_exception(exc: Exception) -> DocumentStatus:
    """Map pipeline failures to explicit lifecycle states."""
    if isinstance(exc, EmbeddingError):
        return DocumentStatus.FAILED_EMBEDDING
    if isinstance(exc, DocumentIngestionError):
        message = str(exc).lower()
        if "index validation" in message or "not retrievable" in message:
            return DocumentStatus.FAILED_INDEXING
        if "extraction" in message or "chunking" in message:
            return DocumentStatus.FAILED_EXTRACTION
    return DocumentStatus.FAILED


def _resolve_embedding_provider(
    pipeline: IngestionPipelineBase,
    override: EmbeddingProvider | None = None,
) -> EmbeddingProvider | None:
    if override is not None:
        return override
    stages = getattr(pipeline, "stages", None) or []
    for stage in stages:
        embedder = getattr(stage, "_embedder", None)
        if embedder is not None:
            return embedder
    return None


class DocumentService:
    """Orchestrate document ingestion, storage, metadata, and lifecycle.

    Depends on abstractions only:
    - ``IngestionPipelineBase``       — pipeline is swappable
    - ``StorageAdapter``              — file storage is swappable
    - ``VectorStore``                 — vector index is swappable
    - ``DocumentRepository``          — metadata persistence (per request)
    - ``LifecycleEventCollector``     — in-process lifecycle events
    - ``ChecksumProvider``            — content identity computation
    - ``DuplicateDetectionPolicy``    — integrity decisions
    - ``DocumentReplacementHandler``  — future replacement operations
    - ``DocumentRetryHandler``        — retry scheduling foundation
    - ``DocumentDiagnosticsService``  — subsystem readiness checks
    """

    def __init__(
        self,
        pipeline: IngestionPipelineBase,
        storage: StorageAdapter,
        vector_store: VectorStore,
        event_collector: LifecycleEventCollector | None = None,
        checksum_provider: ChecksumProvider | None = None,
        integrity_policy: DuplicateDetectionPolicy | None = None,
        replacement_handler: DocumentReplacementHandler | None = None,
        retry_handler: DocumentRetryHandler | None = None,
        diagnostics_service: DocumentDiagnosticsService | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._storage = storage
        self._vector_store = vector_store
        self._events = event_collector or get_lifecycle_event_collector()
        self._checksum_provider = checksum_provider or Sha256ChecksumProvider()
        self._integrity_policy = integrity_policy or DuplicateDetectionPolicy()
        self._replacement_handler = (
            replacement_handler or UnimplementedReplacementHandler()
        )
        self._retry_handler = retry_handler or DefaultDocumentRetryHandler()
        self._diagnostics = diagnostics_service or DocumentDiagnosticsService(
            storage=storage,
            vector_store=vector_store,
            pipeline=pipeline,
            embedding_provider=_resolve_embedding_provider(pipeline),
        )

    @property
    def pipeline(self) -> IngestionPipelineBase:
        """Return the configured ingestion pipeline."""
        return self._pipeline

    @property
    def storage(self) -> StorageAdapter:
        """Return the configured storage adapter."""
        return self._storage

    @property
    def vector_store(self) -> VectorStore:
        """Return the configured vector store."""
        return self._vector_store

    @property
    def event_collector(self) -> LifecycleEventCollector:
        """Return the lifecycle event collector."""
        return self._events

    @property
    def checksum_provider(self) -> ChecksumProvider:
        """Return the configured checksum provider."""
        return self._checksum_provider

    @property
    def integrity_policy(self) -> DuplicateDetectionPolicy:
        """Return the configured integrity policy."""
        return self._integrity_policy

    @property
    def retry_handler(self) -> DocumentRetryHandler:
        """Return the configured retry handler."""
        return self._retry_handler

    @property
    def diagnostics_service(self) -> DocumentDiagnosticsService:
        """Return the document subsystem diagnostics service."""
        return self._diagnostics

    def check_subsystem_readiness(self):
        """Verify document processing dependencies are ready."""
        return self._diagnostics.check_readiness()

    def _pipeline_stages(self) -> list:
        return getattr(self._pipeline, "stages", None) or []

    def _run_processing(
        self,
        filename: str,
        content_type: str,
        content: bytes,
        *,
        tenant_id: str | None = None,
        document_id: str,
        user_id: str | None = None,
        checksum: str | None = None,
    ) -> DocumentProcessingOutcome:
        """Execute ingestion with events, metrics, progress, and structured logging."""
        settings = get_settings()
        context = IngestionContext(
            filename=filename,
            content_type=content_type,
            content=content,
            document_id=document_id,
            checksum=checksum,
            tenant_id=tenant_id or settings.tenant_id,
        )
        stages = self._pipeline_stages()
        first_stage = stages[0].name if stages else None

        self._events.publish(
            DocumentProcessingStarted(
                document_id=document_id,
                user_id=user_id or "system",
                checksum=checksum,
                stage=first_stage,
            )
        )

        processing_start = time.perf_counter()
        failed_stage: str | None = None
        try:
            result = self._pipeline.run(context)
        except Exception as exc:
            failed_stage = self._infer_failed_stage(stages, context.stage_durations)
            total_ms = round((time.perf_counter() - processing_start) * 1000, 2)
            self._events.publish(
                DocumentProcessingFailed(
                    document_id=document_id,
                    user_id=user_id or "system",
                    checksum=checksum,
                    stage=failed_stage,
                    error_message=type(exc).__name__,
                )
            )
            log_with_fields(
                logger,
                logging.ERROR,
                "Document processing failed",
                document_id=document_id,
                user_id=user_id,
                stage=failed_stage,
                processing_duration_ms=total_ms,
                final_status=DocumentStatus.FAILED.value,
            )
            raise

        total_ms = round((time.perf_counter() - processing_start) * 1000, 2)
        metrics = ProcessingMetrics.from_stage_durations(context.stage_durations)
        progress = (
            ProcessingProgress.completed(stages)
            if stages
            else ProcessingProgress.from_stage_durations(stages, context.stage_durations)
        )
        final_status = (
            DocumentStatus.SEARCHABLE if result.indexed else DocumentStatus.STORED
        )

        self._events.publish(
            DocumentProcessingCompleted(
                document_id=document_id,
                user_id=user_id or "system",
                checksum=checksum or result.metadata.checksum,
                total_duration_ms=total_ms,
            )
        )
        log_with_fields(
            logger,
            logging.INFO,
            "Document processing completed",
            document_id=document_id,
            user_id=user_id,
            stage="metadata",
            processing_duration_ms=total_ms,
            final_status=final_status.value,
            validation_duration_ms=metrics.validation_duration_ms,
            extraction_duration_ms=metrics.extraction_duration_ms,
            chunking_duration_ms=metrics.chunking_duration_ms,
            embedding_duration_ms=metrics.embedding_duration_ms,
            indexing_duration_ms=metrics.indexing_duration_ms,
        )
        return DocumentProcessingOutcome(
            result=result,
            metrics=metrics,
            progress=progress,
        )

    @staticmethod
    def _infer_failed_stage(
        stages: list,
        completed_durations: dict[str, float],
    ) -> str | None:
        ordered = [stage.name for stage in sorted(stages, key=lambda s: s.order)]
        for name in ordered:
            if name not in completed_durations:
                return name
        return ordered[-1] if ordered else None

    def _indexing_stage_names(self) -> frozenset[str]:
        return frozenset(
            {"extraction", "chunking", "embedding", "indexing", "index_validation"}
        )

    def reindex_document_vectors(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str,
        content: bytes,
        checksum: str | None = None,
        tenant_id: str | None = None,
    ) -> IngestionContext:
        """Run extraction through index validation for an existing stored document."""
        settings = get_settings()
        self._vector_store.remove_document(document_id)
        context = IngestionContext(
            filename=filename,
            content_type=content_type,
            content=content,
            document_id=document_id,
            checksum=checksum,
            tenant_id=tenant_id or settings.tenant_id,
        )
        indexing_names = self._indexing_stage_names()
        for stage in self._pipeline_stages():
            if stage.name not in indexing_names:
                continue
            context = stage.process(context)
        return context

    def ingest(
        self,
        filename: str,
        content_type: str,
        content: bytes,
        *,
        tenant_id: str | None = None,
        document_id: str | None = None,
    ) -> IngestionResult:
        """Run a document through the full ingestion pipeline."""
        resolved_id = document_id or str(uuid.uuid4())
        outcome = self._run_processing(
            filename,
            content_type,
            content,
            tenant_id=tenant_id,
            document_id=resolved_id,
        )
        return outcome.result

    def _log_integrity_decision(
        self,
        *,
        user_id: str,
        checksum: str,
        decision: IntegrityDecision,
        document_id: str | None = None,
    ) -> None:
        log_with_fields(
            logger,
            logging.INFO,
            "Document integrity evaluated",
            user_id=user_id,
            checksum=checksum,
            integrity_decision=decision.value,
            document_id=document_id,
        )

    def _authorized_existing_document_id(
        self,
        repository: DocumentRepository,
        *,
        document_id: str | None,
        requesting_user: User | None,
    ) -> str | None:
        """Return *document_id* only when *requesting_user* may read that document."""
        if not document_id or requesting_user is None:
            return None
        try:
            existing = repository.get_by_id(uuid.UUID(document_id))
        except (ValueError, TypeError):
            return None
        if existing is None:
            return None
        decision = DocumentAuthorizationService.can_read_document(
            requesting_user,
            existing,
        )
        if not decision.granted:
            return None
        return str(existing.id)

    def upload_document(
        self,
        repository: DocumentRepository,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        uploaded_by: uuid.UUID,
        domain_id: uuid.UUID,
        domain_repository: KnowledgeDomainRepository,
        tenant_id: str | None = None,
        requesting_user: User | None = None,
    ) -> DocumentUploadResult:
        """Upload, ingest, and persist document metadata.

        Integrity is evaluated before the pipeline runs. Exact duplicates
        raise ``DuplicateDocumentError``; conflicts raise integrity errors.
        The public upload API contract remains ``DocumentUploadResult``.

        When a duplicate is detected, ``existing_document_id`` is included on
        the error only if *requesting_user* is authorized to read that document.

        ``domain_id`` is required and must reference an existing Knowledge Domain.
        """
        if domain_repository.get_by_id(domain_id) is None:
            raise DocumentValidationError("Knowledge domain not found.")

        settings = get_settings()
        resolved_tenant = tenant_id or settings.tenant_id
        user_id = str(uploaded_by)
        checksum = self._checksum_provider.compute(content)
        acl_user = requesting_user

        integrity = self._integrity_policy.evaluate(
            repository,
            checksum=checksum,
            filename=filename,
            tenant_id=resolved_tenant,
        )
        self._log_integrity_decision(
            user_id=user_id,
            checksum=checksum,
            decision=integrity.decision,
            document_id=integrity.document_id,
        )

        if integrity.decision == IntegrityDecision.EXACT_DUPLICATE:
            self._events.publish(
                DuplicateDetected(
                    document_id=integrity.document_id or "",
                    user_id=user_id,
                    checksum=checksum,
                )
            )
            raise DuplicateDocumentError(
                filename,
                existing_document_id=self._authorized_existing_document_id(
                    repository,
                    document_id=integrity.document_id,
                    requesting_user=acl_user,
                ),
            )

        if integrity.decision in {
            IntegrityDecision.FILENAME_CONFLICT,
            IntegrityDecision.CONTENT_CHANGED,
        }:
            raise DocumentIntegrityError(integrity.message)

        document_id = uuid.uuid4()
        version_info = DocumentVersionInfo.initial(
            document_id=document_id,
            checksum=checksum,
        )
        try:
            repository.create(
                document_id=version_info.document_id,
                filename=filename,
                content_type=content_type,
                file_size=len(content),
                checksum=checksum,
                storage_path=f"pending/{document_id}",
                uploaded_by=uploaded_by,
                status=DocumentStatus.PROCESSING,
                tenant_id=resolved_tenant,
                version=version_info.version,
                parent_document_id=version_info.parent_document_id,
                owner_id=uploaded_by,
                domain_id=domain_id,
            )
        except IntegrityError:
            # Concurrent upload of the same content for this tenant.
            repository.rollback()
            raced = repository.find_latest_version(
                checksum,
                tenant_id=resolved_tenant,
            )
            raced_id = str(raced.id) if raced is not None else ""
            self._events.publish(
                DuplicateDetected(
                    document_id=raced_id,
                    user_id=user_id,
                    checksum=checksum,
                )
            )
            raise DuplicateDocumentError(
                filename,
                existing_document_id=self._authorized_existing_document_id(
                    repository,
                    document_id=raced_id or None,
                    requesting_user=acl_user,
                ),
            ) from None

        try:
            outcome = self._run_processing(
                filename,
                content_type,
                content,
                tenant_id=resolved_tenant,
                document_id=str(document_id),
                user_id=user_id,
                checksum=checksum,
            )
        except Exception as exc:
            repository.update_status(document_id, _failure_status_for_exception(exc))
            raise

        result = outcome.result
        upload_result = DocumentUploadResult.from_ingestion(result)

        if result.storage_path is None or result.metadata is None:
            repository.update_status(document_id, DocumentStatus.FAILED)
            raise DocumentIngestionError(
                "Document metadata is incomplete after ingestion."
            )

        document = repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")
        document.storage_path = result.storage_path
        document.status = upload_result.status.value
        repository.update(document)

        self._events.publish(
            DocumentUploaded(
                document_id=upload_result.document_id,
                user_id=user_id,
                checksum=checksum,
            )
        )
        if upload_result.status == DocumentStatus.SEARCHABLE:
            self._events.publish(
                DocumentIndexed(
                    document_id=upload_result.document_id,
                    user_id=user_id,
                    checksum=checksum,
                )
            )
        return upload_result

    def retry_document(
        self,
        repository: DocumentRepository,
        document_id: uuid.UUID,
        *,
        retried_by: uuid.UUID,
    ) -> DocumentRetryResult:
        """Re-run ingestion for a failed document without re-uploading.

        Foundation for future background retry workers. Not exposed via API.
        """
        document = repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")
        if not self._retry_handler.can_retry(document.status):
            raise DocumentIngestionError(
                f"Document '{document_id}' is not eligible for retry."
            )

        user_id = str(retried_by)
        if document.status == DocumentStatus.FAILED.value:
            self._retry_handler.schedule_retry(
                repository,
                document_id,
                user_id=user_id,
                event_collector=self._events,
            )

        storage_path = document.storage_path
        if not storage_path or storage_path.startswith("pending/"):
            raise DocumentStorageError(
                f"Stored content unavailable for document '{document_id}'."
            )
        content = self._storage.resolve(storage_path).read_bytes()

        try:
            outcome = self._run_processing(
                document.filename,
                document.content_type,
                content,
                tenant_id=document.tenant_id,
                document_id=str(document_id),
                user_id=user_id,
                checksum=document.checksum,
            )
        except Exception as exc:
            repository.update_status(document_id, _failure_status_for_exception(exc))
            raise

        result = outcome.result
        if result.storage_path is None:
            repository.update_status(document_id, DocumentStatus.FAILED)
            raise DocumentIngestionError(
                "Document metadata is incomplete after retry."
            )

        updated = repository.get_by_id(document_id)
        if updated is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")
        updated.storage_path = result.storage_path
        final_status = (
            DocumentStatus.SEARCHABLE
            if result.indexed
            else DocumentStatus.STORED
        )
        updated.status = final_status.value
        repository.update(updated)

        if final_status == DocumentStatus.SEARCHABLE:
            self._events.publish(
                DocumentIndexed(
                    document_id=str(document_id),
                    user_id=user_id,
                    checksum=document.checksum,
                )
            )

        return self._retry_handler.mark_retry_completed(
            repository,
            document_id,
            user_id=user_id,
            final_status=final_status,
            event_collector=self._events,
        )

    def replace_document(
        self,
        repository: DocumentRepository,
        *,
        document_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
        replaced_by: uuid.UUID,
    ) -> DocumentUploadResult:
        """Replace an existing document. Reserved for a future phase."""
        return self._replacement_handler.replace_document(
            repository,
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            content=content,
            replaced_by=replaced_by,
        )

    def read_document_file(self, document: Document) -> tuple[bytes, str, str]:
        """Return stored file bytes, MIME type, and filename for download/preview."""
        if document.status == DocumentStatus.DELETED.value:
            raise DocumentNotFoundError(f"Document '{document.id}' not found.")

        storage_path = document.storage_path
        if not storage_path or storage_path.startswith("pending/"):
            raise DocumentStorageError(
                f"Stored content unavailable for document '{document.id}'."
            )

        try:
            content = self._storage.resolve(storage_path).read_bytes()
        except StorageError as exc:
            raise DocumentStorageError(
                f"Failed to read stored file for document '{document.id}'."
            ) from exc

        return content, document.content_type, document.filename

    def delete_document(
        self,
        repository: DocumentRepository,
        document_id: uuid.UUID,
        *,
        deleted_by: uuid.UUID,
    ) -> DocumentLifecycleResult:
        """Delete a document from the knowledge base.

        Transaction strategy (no distributed transaction):

        1. Verify the document exists in the repository.
        2. If already ``DELETED``, return idempotent success without side effects.
        3. Remove vectors from ``VectorStore`` (document no longer searchable).
        4. Remove the physical file via ``StorageAdapter``.
        5. Mark metadata status as ``DELETED`` in the repository.
        6. Publish ``DocumentDeleted`` lifecycle event.

        Failure handling:
        - Step 3 failure: abort; metadata and storage unchanged.
        - Step 4 failure: vectors removed but file remains; raises
          ``DocumentStorageError``; metadata unchanged (manual recovery possible).
        - Step 5 failure: vectors and file removed but status not updated;
          raises ``DatabaseError`` wrapper via repository; manual status fix needed.
        """
        document = repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")

        if document.status == DocumentStatus.DELETED.value:
            return DocumentLifecycleResult.deleted(
                str(document_id),
                already_deleted=True,
            )

        self._vector_store.remove_document(str(document_id))

        try:
            # Prefer the stored key; fall back to basename for legacy rows.
            storage_key = document.storage_path or document.filename
            if storage_key and not storage_key.startswith("pending/"):
                self._storage.delete(storage_key)
        except StorageError as exc:
            raise DocumentStorageError(
                f"Failed to delete stored file for document '{document_id}'."
            ) from exc

        updated = repository.mark_deleted(document_id)
        if updated is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")

        self._events.publish(
            DocumentDeleted(
                document_id=str(document_id),
                user_id=str(deleted_by),
                checksum=document.checksum,
            )
        )
        return DocumentLifecycleResult.deleted(str(document_id))

    def list_documents(
        self,
        repository: DocumentRepository,
        *,
        limit: int = DEFAULT_LIST_LIMIT,
        offset: int = 0,
        filename: str | None = None,
        status: DocumentStatus | None = None,
        uploaded_by: uuid.UUID | None = None,
        domain_id: uuid.UUID | None = None,
        viewer: User | None = None,
    ) -> tuple[list[Document], int]:
        """Return a paginated list of document metadata records.

        When *viewer* is provided and is not an Admin/superuser, results are
        filtered through ``DocumentAuthorizationService.can_read_document`` so
        PRIVATE/RESTRICTED documents are not enumerable by unauthorized users.

        ``domain_id`` is applied at the database layer before ACL filtering.
        """
        from app.auth.dependencies import get_user_system_roles
        from app.auth.document_authorization import DocumentAuthorizationService
        from app.auth.role_permissions import SystemRole

        resolved_limit = min(max(limit, 1), MAX_LIST_LIMIT)
        resolved_offset = max(offset, 0)
        filters = DocumentFilter(
            filename=filename,
            status=status,
            uploaded_by=uploaded_by,
            domain_id=domain_id,
        )

        is_admin = False
        if viewer is not None:
            is_admin = bool(viewer.is_superuser) or (
                SystemRole.ADMIN in get_user_system_roles(viewer)
            )

        if viewer is not None and not is_admin:
            # Over-fetch then filter in memory — correct for ACL on small/medium
            # corpora; SQL-level visibility predicates can replace this later.
            candidates, _ = repository.list(
                limit=1000,
                offset=0,
                filters=filters,
            )
            visible = [
                doc
                for doc in candidates
                if DocumentAuthorizationService.can_read_document(
                    viewer, doc
                ).granted
            ]
            total = len(visible)
            return visible[resolved_offset : resolved_offset + resolved_limit], total

        return repository.list(
            limit=resolved_limit,
            offset=resolved_offset,
            filters=filters,
        )

    def get_document(
        self,
        repository: DocumentRepository,
        document_id: uuid.UUID,
    ) -> Document:
        """Return document metadata by ID.

        Soft-deleted documents are treated as not found for normal retrieval.
        """
        document = repository.get_by_id(document_id)
        if document is None or document.status == DocumentStatus.DELETED.value:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")
        return document

    def update_document_domain(
        self,
        repository: DocumentRepository,
        document: Document,
        *,
        domain_id: uuid.UUID | None,
        domain_repository: KnowledgeDomainRepository,
    ) -> Document:
        """Assign or clear the Knowledge Domain for an existing document.

        ``domain_id=None`` clears the assignment (uncategorized). When a domain
        ID is provided it must already exist.
        """
        knowledge_domain = None
        if domain_id is not None:
            knowledge_domain = domain_repository.get_by_id(domain_id)
            if knowledge_domain is None:
                raise DocumentValidationError("Knowledge domain not found.")

        updated = repository.update_domain(document.id, domain_id)
        if updated is None:
            raise DocumentNotFoundError(f"Document '{document.id}' not found.")

        # Keep the relationship in sync for response mapping without an extra query.
        updated.knowledge_domain = knowledge_domain
        return updated


@lru_cache
def get_document_service() -> DocumentService:
    """Return a cached document service instance backed by all default providers."""
    storage = LocalStorage()
    vector_store = _create_default_vector_store()
    pipeline = create_default_pipeline(storage, vector_store=vector_store)
    return DocumentService(
        pipeline=pipeline,
        storage=storage,
        vector_store=vector_store,
    )


def _create_default_vector_store() -> VectorStore:
    from app.config import get_settings
    from app.embeddings.manager import get_embedding_manager
    from app.ingestion.vector_store.faiss_store import FaissVectorStore
    from app.rag.hybrid.bm25 import BM25Index
    from app.rag.hybrid.config import HybridRetrievalSettings
    from app.rag.hybrid.index_store import HybridIndexStore

    settings = get_settings()
    faiss_store = FaissVectorStore(embedding_manager=get_embedding_manager())
    if not settings.hybrid_enabled:
        return faiss_store

    settings.indexes_path.mkdir(parents=True, exist_ok=True)
    hybrid_settings = HybridRetrievalSettings.from_settings(settings)
    bm25_index = BM25Index(
        settings=hybrid_settings,
        persist_path=settings.indexes_path / "bm25_corpus.json",
    )
    bm25_index.load()
    return HybridIndexStore(faiss_store, bm25_index)


def build_document_service(
    storage: StorageAdapter | None = None,
    processor: DocumentProcessor | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: VectorStore | None = None,
    event_collector: LifecycleEventCollector | None = None,
    checksum_provider: ChecksumProvider | None = None,
    integrity_policy: DuplicateDetectionPolicy | None = None,
    replacement_handler: DocumentReplacementHandler | None = None,
    retry_handler: DocumentRetryHandler | None = None,
    diagnostics_service: DocumentDiagnosticsService | None = None,
) -> DocumentService:
    """Build a ``DocumentService`` with custom provider overrides.

    Intended for testing and future configuration-driven wiring.
    """
    resolved_storage = storage or LocalStorage()
    resolved_store = vector_store or _create_default_vector_store()
    pipeline = create_default_pipeline(
        resolved_storage,
        processor=processor,
        embedding_provider=embedding_provider,
        vector_store=resolved_store,
    )
    return DocumentService(
        pipeline=pipeline,
        storage=resolved_storage,
        vector_store=resolved_store,
        event_collector=event_collector,
        checksum_provider=checksum_provider,
        integrity_policy=integrity_policy,
        replacement_handler=replacement_handler,
        retry_handler=retry_handler,
        diagnostics_service=diagnostics_service,
    )
