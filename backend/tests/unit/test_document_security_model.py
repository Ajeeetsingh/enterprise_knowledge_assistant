"""Unit tests for Phase 5.2 — Document Security Model."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Document, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentRepository
from app.documents.status import DocumentStatus
from app.documents.visibility import (
    DEFAULT_VISIBILITY,
    DocumentVisibility,
    resolve_visibility,
)
from tests.constants import TEST_PASSWORD_HASH


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def user_id(db_session: Session) -> uuid.UUID:
    role = Role(name="Admin", description="Admin role")
    user = User(
        email="owner@example.com",
        username="owner",
        full_name="Owner User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    return user.id


def _create_document(
    repository: DocumentRepository,
    uploader: uuid.UUID,
    *,
    department: str | None = None,
    owner_id: uuid.UUID | None = None,
    visibility: DocumentVisibility = DEFAULT_VISIBILITY,
    allowed_roles: list[str] | None = None,
    filename: str = "policy.txt",
) -> Document:
    return repository.create(
        document_id=uuid.uuid4(),
        filename=filename,
        content_type="text/plain",
        file_size=100,
        checksum="abc123",
        storage_path=f"docs/{filename}",
        uploaded_by=uploader,
        status=DocumentStatus.SEARCHABLE,
        department=department,
        owner_id=owner_id,
        visibility=visibility,
        allowed_roles=allowed_roles,
    )


# ---------------------------------------------------------------------------
# DocumentVisibility enum
# ---------------------------------------------------------------------------


class TestDocumentVisibilityEnum:
    def test_all_required_values_exist(self) -> None:
        values = {member.value for member in DocumentVisibility}
        assert values == {"public", "restricted", "private"}

    def test_default_is_restricted(self) -> None:
        assert DEFAULT_VISIBILITY == DocumentVisibility.RESTRICTED

    def test_enum_members_are_strings(self) -> None:
        assert isinstance(DocumentVisibility.PUBLIC, str)
        assert isinstance(DocumentVisibility.RESTRICTED, str)
        assert isinstance(DocumentVisibility.PRIVATE, str)


class TestResolveVisibility:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("public", DocumentVisibility.PUBLIC),
            ("RESTRICTED", DocumentVisibility.RESTRICTED),
            ("Private", DocumentVisibility.PRIVATE),
            (DocumentVisibility.PUBLIC, DocumentVisibility.PUBLIC),
        ],
    )
    def test_resolves_known_values(self, raw: object, expected: DocumentVisibility) -> None:
        assert resolve_visibility(raw) == expected  # type: ignore[arg-type]

    @pytest.mark.parametrize("raw", [None, "", "   ", "confidential", 42])
    def test_returns_none_for_unknown(self, raw: object) -> None:
        assert resolve_visibility(raw) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Document model — security field defaults
# ---------------------------------------------------------------------------


class TestDocumentSecurityDefaults:
    def test_visibility_defaults_to_restricted(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id)
        assert doc.visibility == DocumentVisibility.RESTRICTED.value

    def test_department_defaults_to_none(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id)
        assert doc.department is None

    def test_owner_id_defaults_to_none_when_not_provided(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id)
        assert doc.owner_id is None

    def test_allowed_roles_defaults_to_empty_list(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id)
        assert doc.allowed_roles == []

    def test_visibility_enum_property_returns_correct_member(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, visibility=DocumentVisibility.PUBLIC)
        assert doc.visibility_enum == DocumentVisibility.PUBLIC


# ---------------------------------------------------------------------------
# Department persistence
# ---------------------------------------------------------------------------


class TestDepartmentPersistence:
    def test_department_is_persisted(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, department="HR")
        assert doc.department == "HR"

    def test_department_can_be_updated(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, department="Finance")
        doc.department = "Legal"
        repo.update(doc)
        refreshed = repo.get_by_id(doc.id)
        assert refreshed is not None
        assert refreshed.department == "Legal"

    def test_department_can_be_none(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, department=None)
        assert doc.department is None


# ---------------------------------------------------------------------------
# Owner relationship
# ---------------------------------------------------------------------------


class TestOwnerRelationship:
    def test_owner_id_is_persisted(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, owner_id=user_id)
        assert doc.owner_id == user_id

    def test_owner_relationship_resolves(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, owner_id=user_id)
        assert doc.owner is not None
        assert doc.owner.id == user_id

    def test_uploader_relationship_still_works(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id)
        assert doc.uploader is not None
        assert doc.uploader.id == user_id

    def test_owner_and_uploaded_by_can_differ(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        second_user = User(
            email="second@example.com",
            username="second",
            full_name="Second User",
            password_hash=TEST_PASSWORD_HASH,
            is_active=True,
        )
        db_session.add(second_user)
        db_session.commit()

        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, owner_id=second_user.id)
        assert doc.uploaded_by == user_id
        assert doc.owner_id == second_user.id


# ---------------------------------------------------------------------------
# Visibility persistence
# ---------------------------------------------------------------------------


class TestVisibilityPersistence:
    @pytest.mark.parametrize("vis", list(DocumentVisibility))
    def test_all_visibility_values_persist(
        self, db_session: Session, user_id: uuid.UUID, vis: DocumentVisibility
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, visibility=vis)
        assert doc.visibility == vis.value

    def test_visibility_can_be_updated(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, visibility=DocumentVisibility.PUBLIC)
        doc.visibility = DocumentVisibility.PRIVATE.value
        repo.update(doc)
        refreshed = repo.get_by_id(doc.id)
        assert refreshed is not None
        assert refreshed.visibility == DocumentVisibility.PRIVATE.value


# ---------------------------------------------------------------------------
# allowed_roles persistence
# ---------------------------------------------------------------------------


class TestAllowedRolesPersistence:
    def test_roles_are_persisted_and_retrieved(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, allowed_roles=["Admin", "HR"])
        assert set(doc.allowed_roles) == {"Admin", "HR"}

    def test_empty_roles_list_round_trips(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, allowed_roles=[])
        assert doc.allowed_roles == []

    def test_none_roles_returns_empty_list(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, allowed_roles=None)
        assert doc.allowed_roles == []

    def test_duplicate_roles_deduplicated(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(
            repo, user_id, allowed_roles=["HR", "HR", "Finance"]
        )
        assert set(doc.allowed_roles) == {"HR", "Finance"}

    def test_roles_can_be_updated(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, allowed_roles=["Admin"])
        doc.allowed_roles = ["Admin", "HR", "Finance"]
        repo.update(doc)
        refreshed = repo.get_by_id(doc.id)
        assert refreshed is not None
        assert set(refreshed.allowed_roles) == {"Admin", "HR", "Finance"}

    def test_roles_can_be_cleared(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        doc = _create_document(repo, user_id, allowed_roles=["Admin"])
        doc.allowed_roles = None
        repo.update(doc)
        refreshed = repo.get_by_id(doc.id)
        assert refreshed is not None
        assert refreshed.allowed_roles == []


# ---------------------------------------------------------------------------
# Repository — backward compatibility (no new fields required)
# ---------------------------------------------------------------------------


class TestRepositoryBackwardCompatibility:
    def test_create_without_security_fields_uses_defaults(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        """All new fields are optional — existing callers need no changes."""
        repo = DocumentRepository(db_session)
        doc = repo.create(
            document_id=uuid.uuid4(),
            filename="legacy.txt",
            content_type="text/plain",
            file_size=42,
            checksum="legacy_hash",
            storage_path="docs/legacy.txt",
            uploaded_by=user_id,
            status=DocumentStatus.SEARCHABLE,
        )
        assert doc.visibility == DocumentVisibility.RESTRICTED.value
        assert doc.department is None
        assert doc.owner_id is None
        assert doc.allowed_roles == []

    def test_existing_list_and_detail_operations_unaffected(
        self, db_session: Session, user_id: uuid.UUID
    ) -> None:
        repo = DocumentRepository(db_session)
        _create_document(repo, user_id, filename="a.txt")
        _create_document(repo, user_id, filename="b.txt")
        docs, total = repo.list(limit=10, offset=0)
        assert total == 2
        assert all(hasattr(d, "visibility") for d in docs)
