"""Unit tests for document metadata persistence in DocumentService."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.core.exceptions import DocumentNotFoundError, DocumentValidationError
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository
from app.db.base import Base
from app.db.models import Document, KnowledgeDomain, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentRepository
from tests.helpers.knowledge_domains import domain_upload_kwargs, make_knowledge_domain
from app.documents.status import DocumentStatus
from app.documents.visibility import DocumentVisibility
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.vector_store.base import VectorStore
from app.services.document_service import DocumentService
from app.storage.local import LocalStorage
from unittest.mock import MagicMock


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
    return emb


def _mock_store() -> MagicMock:
    store = MagicMock(spec=VectorStore)
    store.add_chunks.side_effect = (
        lambda chunks, embs, document_id=None: [c.chunk_id for c in chunks]
    )
    return store


def _build_service(storage, store) -> DocumentService:
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor(),
        embedding_provider=_mock_embedder(),
        vector_store=store,
    )
    return DocumentService(pipeline=pipeline, storage=storage, vector_store=store)


def test_upload_document_persists_metadata(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor("Employee handbook."),
        embedding_provider=_mock_embedder(),
        vector_store=store,
    )
    service = DocumentService(pipeline=pipeline, storage=storage, vector_store=store)
    repository = DocumentRepository(db_session)

    upload_result = service.upload_document(
        repository,
        filename="handbook.txt",
        content_type="text/plain",
        content=b"Employee handbook.",
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session),
    )

    persisted = repository.get_by_id(uuid.UUID(upload_result.document_id))

    assert persisted is not None
    assert persisted.filename == "handbook.txt"
    assert persisted.status == DocumentStatus.SEARCHABLE.value
    assert persisted.uploaded_by == uploader_id
    assert persisted.storage_path
    assert persisted.file_size == len(b"Employee handbook.")
    assert persisted.domain_id is not None


def test_upload_rejects_unknown_domain(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    service = _build_service(storage, store)
    repository = DocumentRepository(db_session)

    with pytest.raises(DocumentValidationError, match="Knowledge domain not found"):
        service.upload_document(
            repository,
            filename="handbook.txt",
            content_type="text/plain",
            content=b"Employee handbook.",
            uploaded_by=uploader_id,
            domain_id=uuid.uuid4(),
            domain_repository=KnowledgeDomainRepository(db_session),
        )


def test_get_document_raises_when_missing(db_session: Session, tmp_path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    service = _build_service(storage, store)
    repository = DocumentRepository(db_session)

    with pytest.raises(DocumentNotFoundError):
        service.get_document(repository, uuid.uuid4())


def test_get_document_raises_when_deleted(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    service = _build_service(storage, store)
    repository = DocumentRepository(db_session)

    result = service.upload_document(
        repository,
        filename="gone.txt",
        content_type="text/plain",
        content=b"gone",
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session),
    )
    document_id = uuid.UUID(result.document_id)
    repository.mark_deleted(document_id)

    with pytest.raises(DocumentNotFoundError):
        service.get_document(repository, document_id)


def test_list_documents_returns_paginated_metadata(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    service = _build_service(storage, store)
    repository = DocumentRepository(db_session)

    domain_kwargs = domain_upload_kwargs(db_session)
    service.upload_document(
        repository,
        filename="one.txt",
        content_type="text/plain",
        content=b"one",
        uploaded_by=uploader_id,
        **domain_kwargs,
    )
    service.upload_document(
        repository,
        filename="two.txt",
        content_type="text/plain",
        content=b"two",
        uploaded_by=uploader_id,
        **domain_kwargs,
    )

    documents, total = service.list_documents(repository, limit=1, offset=0)

    assert total == 2
    assert len(documents) == 1


def test_list_documents_filters_by_domain_id(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    service = _build_service(storage, store)
    repository = DocumentRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")
    hr = make_knowledge_domain(db_session, name="Human Resources")

    service.upload_document(
        repository,
        filename="budget.pdf",
        content_type="application/pdf",
        content=b"finance-budget",
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session, finance),
    )
    service.upload_document(
        repository,
        filename="handbook.pdf",
        content_type="application/pdf",
        content=b"hr-handbook",
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session, hr),
    )

    documents, total = service.list_documents(
        repository,
        domain_id=finance.id,
    )

    assert total == 1
    assert documents[0].filename == "budget.pdf"
    assert documents[0].domain_id == finance.id


def test_list_documents_domain_filter_respects_authorization(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    service = _build_service(storage, store)
    repository = DocumentRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")

    service.upload_document(
        repository,
        filename="private-budget.pdf",
        content_type="application/pdf",
        content=b"secret-budget",
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session, finance),
    )
    private_doc = repository.find_by_filename("private-budget.pdf")
    assert private_doc is not None
    private_doc.visibility = DocumentVisibility.PRIVATE.value
    private_doc.owner_id = uploader_id
    db_session.commit()

    outsider = User(
        email="outsider@example.com",
        username="outsider",
        full_name="Outsider",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    outsider.roles.append(Role(name="Employee", description="Employee"))
    db_session.add(outsider)
    db_session.commit()

    documents, total = service.list_documents(
        repository,
        domain_id=finance.id,
        viewer=outsider,
    )

    assert total == 0
    assert documents == []
