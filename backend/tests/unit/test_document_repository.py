"""Unit tests for DocumentRepository."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.db.base import Base
from app.db.models import Document, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
from app.documents.status import DocumentStatus


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


def _create_document(
    repository: DocumentRepository,
    *,
    uploader_id: uuid.UUID,
    filename: str = "policy.txt",
    status: DocumentStatus = DocumentStatus.SEARCHABLE,
) -> Document:
    document_id = uuid.uuid4()
    return repository.create(
        document_id=document_id,
        filename=filename,
        content_type="text/plain",
        file_size=128,
        checksum="abc123",
        storage_path=f"documents/{document_id}/{filename}",
        uploaded_by=uploader_id,
        status=status,
        tenant_id="default",
    )


def test_create_persists_document(db_session: Session, uploader_id: uuid.UUID) -> None:
    repository = DocumentRepository(db_session)

    document = _create_document(repository, uploader_id=uploader_id)

    assert document.id is not None
    assert document.filename == "policy.txt"
    assert document.status == DocumentStatus.SEARCHABLE.value
    assert document.uploaded_by == uploader_id


def test_get_by_id_returns_document(db_session: Session, uploader_id: uuid.UUID) -> None:
    repository = DocumentRepository(db_session)
    created = _create_document(repository, uploader_id=uploader_id)

    fetched = repository.get_by_id(created.id)

    assert fetched is not None
    assert fetched.id == created.id


def test_get_by_id_returns_none_for_missing(
    db_session: Session,
) -> None:
    repository = DocumentRepository(db_session)

    assert repository.get_by_id(uuid.uuid4()) is None


def test_exists_returns_true_for_existing_document(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    created = _create_document(repository, uploader_id=uploader_id)

    assert repository.exists(created.id) is True
    assert repository.exists(uuid.uuid4()) is False


def test_list_returns_paginated_results(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    _create_document(repository, uploader_id=uploader_id, filename="alpha.txt")
    _create_document(repository, uploader_id=uploader_id, filename="beta.txt")
    _create_document(repository, uploader_id=uploader_id, filename="gamma.txt")

    page, total = repository.list(limit=2, offset=0)

    assert total == 3
    assert len(page) == 2


def test_list_filters_by_filename(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    _create_document(repository, uploader_id=uploader_id, filename="handbook.pdf")
    _create_document(repository, uploader_id=uploader_id, filename="notes.txt")

    page, total = repository.list(
        limit=20,
        offset=0,
        filters=DocumentFilter(filename="hand"),
    )

    assert total == 1
    assert page[0].filename == "handbook.pdf"


def test_list_filters_by_status(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    _create_document(
        repository,
        uploader_id=uploader_id,
        filename="indexed.txt",
        status=DocumentStatus.SEARCHABLE,
    )
    _create_document(
        repository,
        uploader_id=uploader_id,
        filename="stored.txt",
        status=DocumentStatus.STORED,
    )

    page, total = repository.list(
        limit=20,
        offset=0,
        filters=DocumentFilter(status=DocumentStatus.STORED),
    )

    assert total == 1
    assert page[0].filename == "stored.txt"


def test_list_filters_by_uploaded_by(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    other_user = User(
        email="other@example.com",
        username="other",
        full_name="Other User",
        password_hash=hash_password("Str0ng!Passw0rd"),
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    _create_document(repository, uploader_id=uploader_id, filename="mine.txt")
    _create_document(repository, uploader_id=other_user.id, filename="theirs.txt")

    page, total = repository.list(
        limit=20,
        offset=0,
        filters=DocumentFilter(uploaded_by=uploader_id),
    )

    assert total == 1
    assert page[0].filename == "mine.txt"


def test_update_status_changes_status(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    created = _create_document(
        repository,
        uploader_id=uploader_id,
        status=DocumentStatus.PROCESSING,
    )

    updated = repository.update_status(created.id, DocumentStatus.SEARCHABLE)

    assert updated is not None
    assert updated.status == DocumentStatus.SEARCHABLE.value


def test_update_status_returns_none_for_missing(
    db_session: Session,
) -> None:
    repository = DocumentRepository(db_session)

    assert repository.update_status(uuid.uuid4(), DocumentStatus.FAILED) is None


def test_mark_deleted_updates_status(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    created = _create_document(repository, uploader_id=uploader_id)

    updated = repository.mark_deleted(created.id)

    assert updated is not None
    assert updated.status == DocumentStatus.DELETED.value


def test_find_by_checksum_returns_matches(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    created = _create_document(
        repository,
        uploader_id=uploader_id,
        filename="alpha.txt",
    )

    matches = repository.find_by_checksum(created.checksum)

    assert len(matches) == 1
    assert matches[0].id == created.id
    assert repository.exists_checksum(created.checksum) is True


def test_find_latest_version_returns_most_recent(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    created = _create_document(repository, uploader_id=uploader_id)

    latest = repository.find_latest_version(created.checksum)

    assert latest is not None
    assert latest.id == created.id


def test_find_by_filename_returns_match(
    db_session: Session,
    uploader_id: uuid.UUID,
) -> None:
    repository = DocumentRepository(db_session)
    created = _create_document(
        repository,
        uploader_id=uploader_id,
        filename="handbook.txt",
    )

    found = repository.find_by_filename("handbook.txt")

    assert found is not None
    assert found.id == created.id
