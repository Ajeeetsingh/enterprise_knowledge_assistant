"""Unit tests for Phase 4.7 production readiness — processing, retry, diagnostics."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.core.exceptions import (
    DocumentIngestionError,
    DocumentStorageError,
    DocumentValidationError,
)
from app.db.base import Base
from app.db.models import Document, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentRepository
from app.documents.dispatcher import LifecycleEventCollector
from app.documents.events import (
    DocumentProcessingCompleted,
    DocumentProcessingFailed,
    DocumentProcessingStarted,
    DocumentRetryCompleted,
    DocumentRetryScheduled,
)
from app.documents.metrics import ProcessingMetrics
from app.documents.progress import ProcessingProgress
from app.documents.retry import DefaultDocumentRetryHandler, DocumentRetryResult
from app.documents.status import DocumentStatus
from app.documents.types import IngestionContext
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import IngestionPipeline, create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.stages import ValidationStage
from app.ingestion.stages.base import PipelineStage
from app.ingestion.vector_store.base import VectorStore
from app.services.document_diagnostics_service import DocumentDiagnosticsService
from app.services.document_service import DocumentService, build_document_service
from app.storage.local import LocalStorage


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def uploader_id(db_session: Session) -> uuid.UUID:
    role = Role(name="Admin", description="Administrator")
    user = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    return user.id


def _mock_processor(text: str = "policy text") -> MagicMock:
    proc = MagicMock(spec=DocumentProcessor)
    proc.process.return_value = text
    return proc


def _mock_embedder() -> MagicMock:
    emb = MagicMock(spec=EmbeddingProvider)
    emb.embed.side_effect = lambda texts: [[0.1] * 4 for _ in texts]
    emb.dimension = 4
    return emb


def _mock_vector_store() -> MagicMock:
    store = MagicMock(spec=VectorStore)
    store.add_chunks.side_effect = lambda chunks, embeddings, document_id=None: [
        c.chunk_id for c in chunks
    ]
    store.size = 0
    store.remove_document.return_value = None
    return store


def _build_service(
    tmp_path,
    *,
    event_collector: LifecycleEventCollector | None = None,
    vector_store: VectorStore | None = None,
    pipeline: IngestionPipeline | None = None,
) -> DocumentService:
    storage = LocalStorage(base_path=tmp_path)
    resolved_store = vector_store or _mock_vector_store()
    resolved_pipeline = pipeline or create_default_pipeline(
        storage,
        processor=_mock_processor("Employee handbook content."),
        embedding_provider=_mock_embedder(),
        vector_store=resolved_store,
    )
    return build_document_service(
        storage=storage,
        processor=_mock_processor("Employee handbook content."),
        embedding_provider=_mock_embedder(),
        vector_store=resolved_store,
        event_collector=event_collector or LifecycleEventCollector(),
    )


class FailingStage(PipelineStage):
    @property
    def name(self) -> str:
        return "failing"

    @property
    def description(self) -> str:
        return "Always fails."

    @property
    def order(self) -> int:
        return 99

    def process(self, context: IngestionContext) -> IngestionContext:
        raise RuntimeError("stage failure")


def test_document_status_includes_retry_pending() -> None:
    assert DocumentStatus.RETRY_PENDING.value == "retry_pending"
    assert DocumentStatus.PROCESSING.value == "processing"
    assert DocumentStatus.FAILED.value == "failed"
    assert DocumentStatus.SEARCHABLE.value == "searchable"
    assert DocumentStatus.DELETED.value == "deleted"


def test_processing_progress_from_stage_durations() -> None:
    stages = [ValidationStage()]
    progress = ProcessingProgress.from_stage_durations(
        stages,
        {"validation": 12.5},
    )
    assert progress.current_stage is None
    assert progress.completed_stages == ["validation"]
    assert progress.total_stages == 1
    assert progress.progress_percentage == 100.0


def test_processing_progress_reports_failed_stage(tmp_path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    stages = create_default_pipeline(
        storage,
        processor=_mock_processor(),
        embedding_provider=_mock_embedder(),
        vector_store=_mock_vector_store(),
    ).stages
    progress = ProcessingProgress.from_stage_durations(
        stages,
        {"validation": 1.0, "storage": 2.0},
        failed_stage="extraction",
    )
    assert progress.current_stage == "extraction"
    assert progress.completed_stages == ["validation", "storage"]
    assert progress.total_stages == 7
    assert progress.progress_percentage == pytest.approx(28.57, rel=0.01)


def test_processing_metrics_from_stage_durations() -> None:
    metrics = ProcessingMetrics.from_stage_durations(
        {
            "validation": 1.0,
            "extraction": 2.5,
            "chunking": 3.0,
            "embedding": 4.0,
            "indexing": 5.0,
        }
    )
    assert metrics.validation_duration_ms == 1.0
    assert metrics.extraction_duration_ms == 2.5
    assert metrics.chunking_duration_ms == 3.0
    assert metrics.embedding_duration_ms == 4.0
    assert metrics.indexing_duration_ms == 5.0
    assert metrics.total_duration_ms == 15.5


def test_pipeline_records_stage_durations(tmp_path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor("Content for metrics."),
        embedding_provider=_mock_embedder(),
        vector_store=_mock_vector_store(),
    )
    context = IngestionContext(
        filename="metrics.txt",
        content_type="text/plain",
        content=b"Content for metrics.",
        tenant_id="default",
    )
    pipeline.run(context)
    assert "validation" in context.stage_durations
    assert "indexing" in context.stage_durations
    assert context.stage_durations["validation"] >= 0


def test_upload_publishes_processing_events(tmp_path, db_session, uploader_id) -> None:
    events = LifecycleEventCollector()
    service = _build_service(tmp_path, event_collector=events)
    repository = DocumentRepository(db_session)

    service.upload_document(
        repository,
        filename="handbook.txt",
        content_type="text/plain",
        content=b"Employee handbook content.",
        uploaded_by=uploader_id,
    )

    operations = [event.operation for event in events.history]
    assert "processing_started" in operations
    assert "processing_completed" in operations
    assert "uploaded" in operations
    assert "indexed" in operations


def test_upload_failure_marks_document_failed(tmp_path, db_session, uploader_id) -> None:
    events = LifecycleEventCollector()
    storage = LocalStorage(base_path=tmp_path)
    failing_pipeline = IngestionPipeline([ValidationStage(), FailingStage()])
    service = build_document_service(
        storage=storage,
        processor=_mock_processor(),
        embedding_provider=_mock_embedder(),
        vector_store=_mock_vector_store(),
        event_collector=events,
    )
    service._pipeline = failing_pipeline
    repository = DocumentRepository(db_session)

    with pytest.raises(DocumentIngestionError):
        service.upload_document(
            repository,
            filename="bad.txt",
            content_type="text/plain",
            content=b"fail",
            uploaded_by=uploader_id,
        )

    documents, total = repository.list(limit=10, offset=0)
    assert total == 1
    assert documents[0].status == DocumentStatus.FAILED.value
    failed_events = [
        e for e in events.history if e.operation == "processing_failed"
    ]
    assert len(failed_events) == 1
    assert failed_events[0].stage == "failing"


def test_retry_handler_schedule_retry(tmp_path, db_session, uploader_id) -> None:
    events = LifecycleEventCollector()
    repository = DocumentRepository(db_session)
    handler = DefaultDocumentRetryHandler()
    document_id = uuid.uuid4()
    repository.create(
        document_id=document_id,
        filename="failed.txt",
        content_type="text/plain",
        file_size=4,
        checksum="abc123",
        storage_path="failed.txt",
        uploaded_by=uploader_id,
        status=DocumentStatus.FAILED,
    )

    result = handler.schedule_retry(
        repository,
        document_id,
        user_id=str(uploader_id),
        event_collector=events,
    )

    assert isinstance(result, DocumentRetryResult)
    assert result.retry_scheduled is True
    assert result.status == DocumentStatus.RETRY_PENDING
    updated = repository.get_by_id(document_id)
    assert updated is not None
    assert updated.status == DocumentStatus.RETRY_PENDING.value
    assert any(e.operation == "retry_scheduled" for e in events.history)


def test_retry_handler_rejects_ineligible_status(
    tmp_path, db_session, uploader_id
) -> None:
    repository = DocumentRepository(db_session)
    handler = DefaultDocumentRetryHandler()
    document_id = uuid.uuid4()
    repository.create(
        document_id=document_id,
        filename="ok.txt",
        content_type="text/plain",
        file_size=4,
        checksum="def456",
        storage_path="ok.txt",
        uploaded_by=uploader_id,
        status=DocumentStatus.SEARCHABLE,
    )

    with pytest.raises(DocumentIngestionError, match="not eligible"):
        handler.schedule_retry(
            repository,
            document_id,
            user_id=str(uploader_id),
            event_collector=LifecycleEventCollector(),
        )


def test_retry_document_reuses_pipeline(tmp_path, db_session, uploader_id) -> None:
    events = LifecycleEventCollector()
    service = _build_service(tmp_path, event_collector=events)
    repository = DocumentRepository(db_session)

    upload = service.upload_document(
        repository,
        filename="retry_me.txt",
        content_type="text/plain",
        content=b"Employee handbook content.",
        uploaded_by=uploader_id,
    )
    document_id = uuid.UUID(upload.document_id)
    repository.update_status(document_id, DocumentStatus.FAILED)

    result = service.retry_document(
        repository,
        document_id,
        retried_by=uploader_id,
    )

    assert result.status == DocumentStatus.SEARCHABLE
    document = repository.get_by_id(document_id)
    assert document is not None
    assert document.status == DocumentStatus.SEARCHABLE.value
    assert any(e.operation == "retry_scheduled" for e in events.history)
    assert any(e.operation == "retry_completed" for e in events.history)


def test_retry_document_requires_stored_content(
    tmp_path, db_session, uploader_id
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)
    document_id = uuid.uuid4()
    repository.create(
        document_id=document_id,
        filename="pending.txt",
        content_type="text/plain",
        file_size=4,
        checksum="pending",
        storage_path=f"pending/{document_id}",
        uploaded_by=uploader_id,
        status=DocumentStatus.FAILED,
    )

    with pytest.raises(DocumentStorageError, match="unavailable"):
        service.retry_document(
            repository,
            document_id,
            retried_by=uploader_id,
        )


def test_diagnostics_service_reports_readiness(tmp_path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    vector_store = _mock_vector_store()
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor(),
        embedding_provider=_mock_embedder(),
        vector_store=vector_store,
    )
    diagnostics = DocumentDiagnosticsService(
        storage=storage,
        vector_store=vector_store,
        pipeline=pipeline,
        embedding_provider=_mock_embedder(),
    )

    report = diagnostics.check_readiness()
    assert report.storage.ready is True
    assert report.vector_store.ready is True
    assert report.embedding_provider.ready is True
    assert report.pipeline.ready is True
    assert report.overall_ready is True


def test_diagnostics_detects_empty_pipeline(tmp_path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    vector_store = _mock_vector_store()
    empty_pipeline = MagicMock()
    empty_pipeline.stage_names = []
    empty_pipeline.stages = []
    diagnostics = DocumentDiagnosticsService(
        storage=storage,
        vector_store=vector_store,
        pipeline=empty_pipeline,
    )
    report = diagnostics.check_readiness()
    assert report.pipeline.ready is False
    assert report.overall_ready is False


def test_document_service_exposes_diagnostics(tmp_path) -> None:
    service = _build_service(tmp_path)
    report = service.check_subsystem_readiness()
    assert report.overall_ready is True


def test_document_service_injects_retry_handler(tmp_path) -> None:
    handler = DefaultDocumentRetryHandler()
    service = build_document_service(
        storage=LocalStorage(base_path=tmp_path),
        retry_handler=handler,
    )
    assert service.retry_handler is handler


def test_validation_failure_before_storage_marks_failed(
    tmp_path, db_session, uploader_id
) -> None:
    events = LifecycleEventCollector()
    service = _build_service(tmp_path, event_collector=events)
    repository = DocumentRepository(db_session)

    with pytest.raises(DocumentValidationError):
        service.upload_document(
            repository,
            filename="empty.txt",
            content_type="text/plain",
            content=b"",
            uploaded_by=uploader_id,
        )

    documents, _ = repository.list(limit=10, offset=0)
    assert len(documents) == 1
    assert documents[0].status == DocumentStatus.FAILED.value


def test_processing_completed_event_includes_duration(tmp_path, db_session, uploader_id) -> None:
    events = LifecycleEventCollector()
    service = _build_service(tmp_path, event_collector=events)
    repository = DocumentRepository(db_session)

    service.upload_document(
        repository,
        filename="duration.txt",
        content_type="text/plain",
        content=b"Employee handbook content.",
        uploaded_by=uploader_id,
    )

    completed = [
        e for e in events.history if isinstance(e, DocumentProcessingCompleted)
    ]
    assert len(completed) == 1
    assert completed[0].total_duration_ms is not None
    assert completed[0].total_duration_ms >= 0


def test_processing_started_event_includes_stage(tmp_path, db_session, uploader_id) -> None:
    events = LifecycleEventCollector()
    service = _build_service(tmp_path, event_collector=events)
    repository = DocumentRepository(db_session)

    service.upload_document(
        repository,
        filename="stage.txt",
        content_type="text/plain",
        content=b"Employee handbook content.",
        uploaded_by=uploader_id,
    )

    started = [
        e for e in events.history if isinstance(e, DocumentProcessingStarted)
    ]
    assert len(started) == 1
    assert started[0].stage == "validation"
