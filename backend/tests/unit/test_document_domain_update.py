"""Unit tests for document Knowledge Domain assignment (follow-up)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.documents import update_document_domain
from app.auth.dependencies import AUTHORIZATION_DENIED_MESSAGE
from app.core.exceptions import DocumentValidationError
from app.db.base import Base
from app.db.models import Document, KnowledgeDomain, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository
from app.documents.status import DocumentStatus
from app.documents.visibility import DocumentVisibility
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.vector_store.base import VectorStore
from app.schemas.documents import DocumentDomainUpdateRequest
from app.services.document_service import DocumentService
from app.storage.local import LocalStorage
from tests.constants import TEST_PASSWORD_HASH
from tests.helpers.knowledge_domains import make_knowledge_domain


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
def admin_user(db_session: Session) -> User:
    role = Role(name="Admin", description="Administrator")
    user = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
        is_superuser=False,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def employee_user(db_session: Session) -> User:
    role = Role(name="Employee", description="Employee")
    user = User(
        email="employee@example.com",
        username="employee",
        full_name="Employee User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_document(
    repository: DocumentRepository,
    *,
    uploader_id: uuid.UUID,
    filename: str = "policy.pdf",
    domain_id: uuid.UUID | None = None,
    visibility: DocumentVisibility = DocumentVisibility.PUBLIC,
) -> Document:
    document_id = uuid.uuid4()
    return repository.create(
        document_id=document_id,
        filename=filename,
        content_type="application/pdf",
        file_size=128,
        checksum=f"checksum-{document_id}",
        storage_path=f"documents/{document_id}/{filename}",
        uploaded_by=uploader_id,
        status=DocumentStatus.SEARCHABLE,
        tenant_id="default",
        domain_id=domain_id,
        visibility=visibility,
        owner_id=uploader_id,
    )


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


def test_admin_assigns_uncategorized_document_to_finance(
    db_session: Session,
    admin_user: User,
    tmp_path,
) -> None:
    repository = DocumentRepository(db_session)
    domain_repository = KnowledgeDomainRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")
    document = _create_document(repository, uploader_id=admin_user.id, domain_id=None)
    service = _build_service(tmp_path)

    response = update_document_domain(
        document_id=document.id,
        body=DocumentDomainUpdateRequest(domain_id=finance.id),
        current_user=admin_user,
        document=document,
        document_service=service,
        repository=repository,
        domain_repository=domain_repository,
    )

    assert response.domain_id == finance.id
    assert response.domain_name == "Finance"
    persisted = repository.get_by_id(document.id)
    assert persisted is not None
    assert persisted.domain_id == finance.id


def test_admin_can_reassign_between_domains(
    db_session: Session,
    admin_user: User,
    tmp_path,
) -> None:
    repository = DocumentRepository(db_session)
    domain_repository = KnowledgeDomainRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")
    hr = make_knowledge_domain(db_session, name="Human Resources")
    governance = make_knowledge_domain(db_session, name="Enterprise Governance")
    document = _create_document(
        repository,
        uploader_id=admin_user.id,
        domain_id=finance.id,
    )
    service = _build_service(tmp_path)

    mid = update_document_domain(
        document_id=document.id,
        body=DocumentDomainUpdateRequest(domain_id=hr.id),
        current_user=admin_user,
        document=document,
        document_service=service,
        repository=repository,
        domain_repository=domain_repository,
    )
    assert mid.domain_name == "Human Resources"

    final = update_document_domain(
        document_id=document.id,
        body=DocumentDomainUpdateRequest(domain_id=governance.id),
        current_user=admin_user,
        document=repository.get_by_id(document.id),
        document_service=service,
        repository=repository,
        domain_repository=domain_repository,
    )
    assert final.domain_name == "Enterprise Governance"
    assert repository.get_by_id(document.id).domain_id == governance.id


def test_nonexistent_domain_is_rejected(
    db_session: Session,
    admin_user: User,
    tmp_path,
) -> None:
    repository = DocumentRepository(db_session)
    domain_repository = KnowledgeDomainRepository(db_session)
    document = _create_document(repository, uploader_id=admin_user.id)
    service = _build_service(tmp_path)

    with pytest.raises(DocumentValidationError, match="Knowledge domain not found"):
        service.update_document_domain(
            repository,
            document,
            domain_id=uuid.uuid4(),
            domain_repository=domain_repository,
        )


def test_non_admin_cannot_change_domain(
    db_session: Session,
    admin_user: User,
    employee_user: User,
    tmp_path,
) -> None:
    repository = DocumentRepository(db_session)
    domain_repository = KnowledgeDomainRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")
    document = _create_document(repository, uploader_id=admin_user.id)
    service = _build_service(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        update_document_domain(
            document_id=document.id,
            body=DocumentDomainUpdateRequest(domain_id=finance.id),
            current_user=employee_user,
            document=document,
            document_service=service,
            repository=repository,
            domain_repository=domain_repository,
        )

    assert exc_info.value.status_code == 403
    assert "administrator" in str(exc_info.value.detail).lower()
    assert repository.get_by_id(document.id).domain_id is None


def test_domain_filter_reflects_reassignment(
    db_session: Session,
    admin_user: User,
    tmp_path,
) -> None:
    repository = DocumentRepository(db_session)
    domain_repository = KnowledgeDomainRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")
    document = _create_document(repository, uploader_id=admin_user.id, domain_id=None)
    service = _build_service(tmp_path)

    before, before_total = repository.list(
        limit=20,
        offset=0,
        filters=DocumentFilter(domain_id=finance.id),
    )
    assert before_total == 0
    assert before == []

    update_document_domain(
        document_id=document.id,
        body=DocumentDomainUpdateRequest(domain_id=finance.id),
        current_user=admin_user,
        document=document,
        document_service=service,
        repository=repository,
        domain_repository=domain_repository,
    )

    after, after_total = repository.list(
        limit=20,
        offset=0,
        filters=DocumentFilter(domain_id=finance.id),
    )
    assert after_total == 1
    assert after[0].id == document.id


def test_clear_domain_sets_null(
    db_session: Session,
    admin_user: User,
    tmp_path,
) -> None:
    repository = DocumentRepository(db_session)
    domain_repository = KnowledgeDomainRepository(db_session)
    finance = make_knowledge_domain(db_session, name="Finance")
    document = _create_document(
        repository,
        uploader_id=admin_user.id,
        domain_id=finance.id,
    )
    service = _build_service(tmp_path)

    response = update_document_domain(
        document_id=document.id,
        body=DocumentDomainUpdateRequest(domain_id=None),
        current_user=admin_user,
        document=document,
        document_service=service,
        repository=repository,
        domain_repository=domain_repository,
    )

    assert response.domain_id is None
    assert response.domain_name is None
    assert repository.get_by_id(document.id).domain_id is None


def test_private_document_acl_still_enforced_via_dependency_path(
    db_session: Session,
    admin_user: User,
    employee_user: User,
) -> None:
    """Non-admins remain blocked by document ACL for private documents."""
    from app.auth.document_authorization import DocumentAuthorizationService

    repository = DocumentRepository(db_session)
    document = _create_document(
        repository,
        uploader_id=admin_user.id,
        visibility=DocumentVisibility.PRIVATE,
    )

    decision = DocumentAuthorizationService.can_update_document(
        employee_user, document
    )
    assert decision.granted is False
    # Admin path message constant remains the shared denial string for ACL.
    assert AUTHORIZATION_DENIED_MESSAGE
