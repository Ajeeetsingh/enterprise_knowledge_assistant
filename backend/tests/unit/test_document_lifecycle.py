"""Unit tests for document lifecycle management."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.core.exceptions import DocumentNotFoundError, DocumentStorageError, StorageError
from app.db.base import Base
from app.db.models import Document, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentRepository
from app.documents.dispatcher import LifecycleEventCollector
from app.documents.events import DocumentDeleted, DocumentIndexed, DocumentUploaded
from app.documents.lifecycle import DocumentLifecycleResult
from app.documents.status import DocumentStatus
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.vector_store.base import VectorStore
from app.services.document_service import DocumentService
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
        password_hash=hash_password("Str0ng!Passw0rd"),
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
    return emb


def _mock_vector_store() -> MagicMock:
    store = MagicMock(spec=VectorStore)
    store.add_chunks.side_effect = lambda chunks, embeddings, document_id=None: [
        c.chunk_id for c in chunks
    ]
    store.size = 0
    return store


def _build_service(
    tmp_path,
    *,
    vector_store: VectorStore | None = None,
    event_collector: LifecycleEventCollector | None = None,
) -> DocumentService:
    storage = LocalStorage(base_path=tmp_path)
    resolved_store = vector_store or _mock_vector_store()
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor("Employee handbook."),
        embedding_provider=_mock_embedder(),
        vector_store=resolved_store,
    )
    return DocumentService(
        pipeline=pipeline,
        storage=storage,
        vector_store=resolved_store,
        event_collector=event_collector or LifecycleEventCollector(),
    )


def _persist_searchable_document(
    service: DocumentService,
    repository: DocumentRepository,
    uploader_id: uuid.UUID,
) -> uuid.UUID:
    upload_result = service.upload_document(
        repository,
        filename="handbook.txt",
        content_type="text/plain",
        content=b"Employee handbook.",
        uploaded_by=uploader_id,
    )
    return uuid.UUID(upload_result.document_id)


def test_delete_document_removes_vectors_storage_and_updates_status(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    vector_store = _mock_vector_store()
    service = _build_service(tmp_path, vector_store=vector_store)
    repository = DocumentRepository(db_session)
    document_id = _persist_searchable_document(service, repository, uploader_id)

    result = service.delete_document(
        repository,
        document_id,
        deleted_by=uploader_id,
    )

    assert isinstance(result, DocumentLifecycleResult)
    assert result.status == DocumentStatus.DELETED
    persisted = repository.get_by_id(document_id)
    assert persisted is not None
    assert persisted.status == DocumentStatus.DELETED.value
    vector_store.remove_document.assert_called_once_with(str(document_id))
    assert not service.storage.exists("handbook.txt")


def test_delete_document_emits_lifecycle_event(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    collector = LifecycleEventCollector()
    service = _build_service(tmp_path, event_collector=collector)
    repository = DocumentRepository(db_session)
    document_id = _persist_searchable_document(service, repository, uploader_id)

    service.delete_document(repository, document_id, deleted_by=uploader_id)

    deleted_events = [e for e in collector.history if isinstance(e, DocumentDeleted)]
    assert len(deleted_events) == 1
    assert deleted_events[0].document_id == str(document_id)
    assert deleted_events[0].user_id == str(uploader_id)
    assert deleted_events[0].operation == "deleted"


def test_upload_emits_upload_and_indexed_events(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    collector = LifecycleEventCollector()
    service = _build_service(tmp_path, event_collector=collector)
    repository = DocumentRepository(db_session)

    service.upload_document(
        repository,
        filename="handbook.txt",
        content_type="text/plain",
        content=b"Employee handbook.",
        uploaded_by=uploader_id,
    )

    assert any(isinstance(e, DocumentUploaded) for e in collector.history)
    assert any(isinstance(e, DocumentIndexed) for e in collector.history)


def test_delete_already_deleted_document_is_idempotent(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    vector_store = _mock_vector_store()
    service = _build_service(tmp_path, vector_store=vector_store)
    repository = DocumentRepository(db_session)
    document_id = _persist_searchable_document(service, repository, uploader_id)

    first = service.delete_document(repository, document_id, deleted_by=uploader_id)
    second = service.delete_document(repository, document_id, deleted_by=uploader_id)

    assert first.status == DocumentStatus.DELETED
    assert second.status == DocumentStatus.DELETED
    assert "already deleted" in second.message.lower()
    vector_store.remove_document.assert_called_once()


def test_delete_missing_document_raises_not_found(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)

    with pytest.raises(DocumentNotFoundError):
        service.delete_document(
            repository,
            uuid.uuid4(),
            deleted_by=uploader_id,
        )


def test_delete_raises_when_storage_delete_fails(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)
    document_id = _persist_searchable_document(service, repository, uploader_id)

    def fail_delete(_relative_path: str) -> None:
        raise StorageError("simulated storage failure")

    monkeypatch.setattr(service.storage, "delete", fail_delete)

    with pytest.raises(DocumentStorageError):
        service.delete_document(repository, document_id, deleted_by=uploader_id)

    persisted = repository.get_by_id(document_id)
    assert persisted is not None
    assert persisted.status == DocumentStatus.SEARCHABLE.value
