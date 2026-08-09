"""Contract tests: upload + Knowledge Domain remain decoupled backend operations."""

from __future__ import annotations

import inspect
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import knowledge_domains as knowledge_domains_api
from app.api.v1.documents import upload_document
from app.core.exceptions import DocumentValidationError
from app.db.base import Base
from app.db.models import Document, KnowledgeDomain, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.vector_store.base import VectorStore
from app.services.document_service import DocumentService
from app.services.knowledge_domain_service import KnowledgeDomainService
from app.storage.local import LocalStorage
from tests.constants import TEST_PASSWORD_HASH
from tests.helpers.knowledge_domains import domain_upload_kwargs, make_knowledge_domain


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


def _build_service(tmp_path) -> DocumentService:
    storage = LocalStorage(base_path=tmp_path)
    processor = MagicMock(spec=DocumentProcessor)
    processor.process.return_value = "text"
    embedder = MagicMock(spec=EmbeddingProvider)
    embedder.embed.side_effect = lambda texts: [[0.1] * 4 for _ in texts]
    store = MagicMock(spec=VectorStore)
    store.add_chunks.side_effect = (
        lambda chunks, embs, document_id=None: [c.chunk_id for c in chunks]
    )
    pipeline = create_default_pipeline(
        storage,
        processor=processor,
        embedding_provider=embedder,
        vector_store=store,
    )
    return DocumentService(pipeline=pipeline, storage=storage, vector_store=store)


def test_create_domain_api_does_not_depend_on_document_upload() -> None:
    """Create-domain endpoint must not take document/upload dependencies."""
    params = inspect.signature(knowledge_domains_api.create_knowledge_domain).parameters
    assert "document_service" not in params
    assert "repository" not in params
    assert "file" not in params
    source = inspect.getsource(knowledge_domains_api.create_knowledge_domain)
    assert "upload_document" not in source
    assert "DocumentService" not in source


def test_create_domain_service_does_not_invoke_upload(
    db_session: Session,
    tmp_path,
) -> None:
    domain_service = KnowledgeDomainService(KnowledgeDomainRepository(db_session))
    document_service = _build_service(tmp_path)

    with patch.object(
        document_service,
        "upload_document",
        wraps=document_service.upload_document,
    ) as upload_spy:
        domain = domain_service.create_domain(
            name="Procurement",
            description="Vendor policies",
        )
        upload_spy.assert_not_called()

    assert domain.name == "Procurement"
    assert domain_service._repository.get_by_id(domain.id) is not None


def test_upload_with_valid_domain_persists_domain_id(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")

    result = service.upload_document(
        repository,
        filename="expense-policy.pdf",
        content_type="application/pdf",
        content=b"expense-policy-content",
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session, finance),
    )

    persisted = repository.get_by_id(uuid.UUID(result.document_id))
    assert persisted is not None
    assert persisted.domain_id == finance.id


def test_upload_rejects_unknown_domain_id(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)

    with pytest.raises(DocumentValidationError, match="Knowledge domain not found"):
        service.upload_document(
            repository,
            filename="notes.txt",
            content_type="text/plain",
            content=b"notes",
            uploaded_by=uploader_id,
            domain_id=uuid.uuid4(),
            domain_repository=KnowledgeDomainRepository(db_session),
        )


def test_upload_endpoint_requires_domain_id_form_field() -> None:
    """API contract: domain_id is a required multipart Form field."""
    params = inspect.signature(upload_document).parameters
    assert "domain_id" in params
    default = params["domain_id"].default
    assert default is not inspect.Parameter.empty
    assert type(default).__name__ == "Form"
    assert default.is_required() is True
    annotation = params["domain_id"].annotation
    assert annotation is uuid.UUID or annotation in {uuid.UUID, "uuid.UUID"}


def test_multiple_uploads_receive_same_domain_id(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")
    kwargs = domain_upload_kwargs(db_session, finance)

    first = service.upload_document(
        repository,
        filename="a.pdf",
        content_type="application/pdf",
        content=b"file-a-content",
        uploaded_by=uploader_id,
        **kwargs,
    )
    second = service.upload_document(
        repository,
        filename="b.pdf",
        content_type="application/pdf",
        content=b"file-b-content",
        uploaded_by=uploader_id,
        **kwargs,
    )

    doc_a = repository.get_by_id(uuid.UUID(first.document_id))
    doc_b = repository.get_by_id(uuid.UUID(second.document_id))
    assert doc_a is not None and doc_b is not None
    assert doc_a.domain_id == finance.id
    assert doc_b.domain_id == finance.id
    assert doc_a.domain_id == doc_b.domain_id


def test_create_domain_does_not_modify_existing_documents(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")
    upload = service.upload_document(
        repository,
        filename="kept.pdf",
        content_type="application/pdf",
        content=b"kept-content",
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session, finance),
    )
    before = repository.get_by_id(uuid.UUID(upload.document_id))
    assert before is not None
    original_domain = before.domain_id

    KnowledgeDomainService(KnowledgeDomainRepository(db_session)).create_domain(
        name="Procurement",
    )

    after = repository.get_by_id(uuid.UUID(upload.document_id))
    assert after is not None
    assert after.domain_id == original_domain == finance.id
