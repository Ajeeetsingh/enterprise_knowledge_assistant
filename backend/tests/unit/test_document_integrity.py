"""Unit tests for document integrity policy and upload integration."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.core.exceptions import DocumentIntegrityError, DuplicateDocumentError
from app.db.base import Base
from app.db.models import Document, KnowledgeDomain, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentRepository
from tests.helpers.knowledge_domains import domain_upload_kwargs
from app.documents.checksum import Sha256ChecksumProvider
from app.documents.dispatcher import LifecycleEventCollector
from app.documents.events import DuplicateDetected
from app.documents.integrity import (
    DuplicateDetectionPolicy,
    IntegrityDecision,
)
from app.documents.status import DocumentStatus
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.vector_store.base import VectorStore
from app.mappers.documents import map_to_integrity_response
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


def _mock_vector_store() -> MagicMock:
    store = MagicMock(spec=VectorStore)
    store.add_chunks.side_effect = (
        lambda chunks, embs, document_id=None: [c.chunk_id for c in chunks]
    )
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
        checksum_provider=Sha256ChecksumProvider(),
        integrity_policy=DuplicateDetectionPolicy(),
    )


def _persist_document(
    repository: DocumentRepository,
    *,
    uploader_id: uuid.UUID,
    filename: str,
    content: bytes,
    tenant_id: str = "default",
) -> Document:
    checksum = Sha256ChecksumProvider().compute(content)
    return repository.create(
        document_id=uuid.uuid4(),
        filename=filename,
        content_type="text/plain",
        file_size=len(content),
        checksum=checksum,
        storage_path=f"/stored/{filename}",
        uploaded_by=uploader_id,
        status=DocumentStatus.SEARCHABLE,
        tenant_id=tenant_id,
    )


def test_policy_detects_new_document(db_session: Session) -> None:
    policy = DuplicateDetectionPolicy()
    repository = DocumentRepository(db_session)
    checksum = Sha256ChecksumProvider().compute(b"new content")

    result = policy.evaluate(
        repository,
        checksum=checksum,
        filename="new.txt",
    )

    assert result.decision == IntegrityDecision.NEW_DOCUMENT
    assert result.document_id is None


def test_policy_detects_exact_duplicate(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    content = b"duplicate content"
    existing = _persist_document(
        repository,
        uploader_id=uploader_id,
        filename="original.txt",
        content=content,
    )
    checksum = Sha256ChecksumProvider().compute(content)
    policy = DuplicateDetectionPolicy()

    result = policy.evaluate(
        repository,
        checksum=checksum,
        filename="copy.txt",
        tenant_id="default",
    )

    assert result.decision == IntegrityDecision.EXACT_DUPLICATE
    assert result.document_id == str(existing.id)
    assert "already been uploaded" in result.message


def test_policy_detects_filename_conflict(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    _persist_document(
        repository,
        uploader_id=uploader_id,
        filename="policy.txt",
        content=b"original content",
    )
    checksum = Sha256ChecksumProvider().compute(b"different content")
    policy = DuplicateDetectionPolicy()

    result = policy.evaluate(
        repository,
        checksum=checksum,
        filename="policy.txt",
        tenant_id="default",
    )

    assert result.decision == IntegrityDecision.FILENAME_CONFLICT


def test_policy_allows_same_checksum_in_different_tenant(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    content = b"shared across orgs"
    _persist_document(
        repository,
        uploader_id=uploader_id,
        filename="shared.txt",
        content=content,
        tenant_id="tenant-a",
    )
    checksum = Sha256ChecksumProvider().compute(content)
    policy = DuplicateDetectionPolicy()

    result = policy.evaluate(
        repository,
        checksum=checksum,
        filename="shared-copy.txt",
        tenant_id="tenant-b",
    )

    assert result.decision == IntegrityDecision.NEW_DOCUMENT


def test_policy_ignores_soft_deleted_duplicates(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    content = b"deleted then reuploaded"
    existing = _persist_document(
        repository,
        uploader_id=uploader_id,
        filename="gone.txt",
        content=content,
    )
    repository.mark_deleted(existing.id)
    checksum = Sha256ChecksumProvider().compute(content)
    policy = DuplicateDetectionPolicy()

    result = policy.evaluate(
        repository,
        checksum=checksum,
        filename="gone-again.txt",
        tenant_id="default",
    )

    assert result.decision == IntegrityDecision.NEW_DOCUMENT


def test_repository_find_by_checksum_and_latest_version(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    content = b"shared content"
    checksum = Sha256ChecksumProvider().compute(content)
    first = _persist_document(
        repository,
        uploader_id=uploader_id,
        filename="v1.txt",
        content=content,
    )

    assert repository.exists_checksum(checksum, tenant_id="default") is True
    matches = repository.find_by_checksum(checksum, tenant_id="default")
    assert len(matches) == 1
    assert repository.find_latest_version(checksum, tenant_id="default").id == first.id


def test_upload_exact_duplicate_raises_conflict(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    vector_store = _mock_vector_store()
    collector = LifecycleEventCollector()
    service = _build_service(
        tmp_path,
        vector_store=vector_store,
        event_collector=collector,
    )
    repository = DocumentRepository(db_session)
    content = b"Employee handbook."
    uploader = db_session.get(User, uploader_id)

    first = service.upload_document(
        repository,
        filename="handbook.txt",
        content_type="text/plain",
        content=content,
        uploaded_by=uploader_id,
        requesting_user=uploader,
        **domain_upload_kwargs(db_session),
    )

    with pytest.raises(DuplicateDocumentError) as exc_info:
        service.upload_document(
            repository,
            filename="handbook-copy.txt",
            content_type="text/plain",
            content=content,
            uploaded_by=uploader_id,
            requesting_user=uploader,
            **domain_upload_kwargs(db_session),
        )

    assert exc_info.value.code == "DUPLICATE_DOCUMENT"
    assert "handbook-copy.txt has already been uploaded." in exc_info.value.public_message
    assert exc_info.value.existing_document_id == first.document_id
    assert vector_store.add_chunks.call_count == 1
    assert any(isinstance(event, DuplicateDetected) for event in collector.history)


def test_duplicate_omits_existing_id_when_requester_unauthorized(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    from app.documents.visibility import DocumentVisibility

    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)
    content = b"restricted duplicate payload"

    service.upload_document(
        repository,
        filename="secret.txt",
        content_type="text/plain",
        content=content,
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session),
    )
    # Make the stored document private so a different non-owner cannot read it.
    stored = repository.find_by_filename("secret.txt", tenant_id="default")
    assert stored is not None
    stored.visibility = DocumentVisibility.PRIVATE.value
    stored.owner_id = uploader_id
    repository.update(stored)

    outsider_role = Role(name="Employee", description="Employee")
    outsider = User(
        email="employee@example.com",
        username="employee",
        full_name="Employee User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    outsider.roles.append(outsider_role)
    db_session.add_all([outsider_role, outsider])
    db_session.commit()
    db_session.refresh(outsider)

    with pytest.raises(DuplicateDocumentError) as exc_info:
        service.upload_document(
            repository,
            filename="secret-copy.txt",
            content_type="text/plain",
            content=content,
            uploaded_by=outsider.id,
            requesting_user=outsider,
            **domain_upload_kwargs(db_session),
        )

    assert exc_info.value.code == "DUPLICATE_DOCUMENT"
    assert exc_info.value.existing_document_id is None


def test_upload_same_content_renamed_is_duplicate(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)
    content = b"identical bytes"

    service.upload_document(
        repository,
        filename="original.txt",
        content_type="text/plain",
        content=content,
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session),
    )

    with pytest.raises(DuplicateDocumentError) as exc_info:
        service.upload_document(
            repository,
            filename="renamed.txt",
            content_type="text/plain",
            content=content,
            uploaded_by=uploader_id,
            **domain_upload_kwargs(db_session),
        )

    assert "renamed.txt has already been uploaded." == exc_info.value.public_message


def test_upload_same_filename_different_content_still_conflicts(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)

    service.upload_document(
        repository,
        filename="policy.txt",
        content_type="text/plain",
        content=b"original content",
        uploaded_by=uploader_id,
        **domain_upload_kwargs(db_session),
    )

    with pytest.raises(DocumentIntegrityError) as exc_info:
        service.upload_document(
            repository,
            filename="policy.txt",
            content_type="text/plain",
            content=b"different content",
            uploaded_by=uploader_id,
            **domain_upload_kwargs(db_session),
        )

    assert not isinstance(exc_info.value, DuplicateDocumentError)


def test_upload_maps_unique_constraint_race_to_duplicate_error(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    """Pre-check miss + unique index hit must still return DUPLICATE_DOCUMENT."""
    from unittest.mock import patch

    from sqlalchemy.exc import IntegrityError

    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)

    with (
        patch.object(repository, "find_latest_version", return_value=None),
        patch.object(repository, "find_by_filename", return_value=None),
        patch.object(
            repository,
            "create",
            side_effect=IntegrityError("duplicate", {}, None),
        ),
        patch.object(repository, "rollback") as rollback,
    ):
        with pytest.raises(DuplicateDocumentError) as exc_info:
            service.upload_document(
                repository,
                filename="racy.txt",
                content_type="text/plain",
                content=b"race content",
                uploaded_by=uploader_id,
                **domain_upload_kwargs(db_session),
            )

    assert exc_info.value.code == "DUPLICATE_DOCUMENT"
    assert exc_info.value.public_message == "racy.txt has already been uploaded."
    rollback.assert_called_once()


def test_map_to_integrity_response() -> None:
    from app.documents.integrity import DocumentIntegrityResult

    existing_id = uuid.uuid4()
    result = DocumentIntegrityResult(
        decision=IntegrityDecision.EXACT_DUPLICATE,
        checksum="abc123",
        filename="policy.txt",
        message="duplicate",
        document_id=str(existing_id),
        existing_filename="policy.txt",
    )

    response = map_to_integrity_response(result)

    assert response.decision == "exact_duplicate"
    assert response.checksum == "abc123"
    assert response.document_id == str(existing_id)


def test_replace_document_not_implemented(
    db_session: Session,
    uploader_id: uuid.UUID,
    tmp_path,
) -> None:
    service = _build_service(tmp_path)
    repository = DocumentRepository(db_session)

    with pytest.raises(NotImplementedError):
        service.replace_document(
            repository,
            document_id=uuid.uuid4(),
            filename="policy.txt",
            content_type="text/plain",
            content=b"replacement",
            replaced_by=uploader_id,
        )
