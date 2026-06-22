"""Integration tests for Phase 5.4 — Document-Level Authorization."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTHORIZATION_DENIED_MESSAGE
from app.db.models import Document, Role, User
from app.db.repositories.document_repository import DocumentRepository
from app.dependencies import get_db, get_document_repository, get_document_service_dep
from app.documents.status import DocumentStatus
from app.documents.visibility import DocumentVisibility
from app.main import app
from tests.constants import TEST_PASSWORD_HASH
from tests.integration.conftest import access_token_for, bearer_headers

DOCUMENTS_URL = "/api/v1/documents"


def _document_url(document_id: uuid.UUID) -> str:
    return f"{DOCUMENTS_URL}/{document_id}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def finance_role(db_session: Session) -> Role:
    role = Role(name="Finance", description="Finance team access")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def finance_user(db_session: Session, finance_role: Role) -> User:
    user = User(
        email="finance@example.com",
        username="finance",
        full_name="Finance User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(finance_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_document(
    db_session: Session,
    uploaded_by: uuid.UUID,
    *,
    visibility: DocumentVisibility = DocumentVisibility.RESTRICTED,
    allowed_roles: list[str] | None = None,
    owner_id: uuid.UUID | None = None,
    filename: str = "policy.txt",
) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename=filename,
        content_type="text/plain",
        file_size=42,
        checksum=f"hash-{uuid.uuid4().hex[:8]}",
        storage_path=f"docs/{filename}",
        status=DocumentStatus.SEARCHABLE.value,
        uploaded_by=uploaded_by,
        owner_id=owner_id,
        visibility=visibility.value,
    )
    doc.allowed_roles = allowed_roles
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture
def doc_client(db_session: Session) -> TestClient:
    """Client with DB override — no document service mock (uses real repo)."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Admin always has access
# ---------------------------------------------------------------------------

class TestAdminDocumentAccess:
    def test_admin_can_read_restricted_document(
        self,
        doc_client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            admin_user.id,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
            owner_id=admin_user.id,
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(admin_user)),
        )

        assert response.status_code == 200

    def test_admin_can_read_private_document(
        self,
        doc_client: TestClient,
        admin_user: User,
        active_user: User,
        db_session: Session,
    ) -> None:
        # Document owned by active_user (Employee), not admin
        doc = _make_document(
            db_session,
            active_user.id,
            visibility=DocumentVisibility.PRIVATE,
            owner_id=active_user.id,
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(admin_user)),
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Owner access
# ---------------------------------------------------------------------------

class TestOwnerDocumentAccess:
    def test_owner_can_read_own_private_document(
        self,
        doc_client: TestClient,
        active_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            active_user.id,
            visibility=DocumentVisibility.PRIVATE,
            owner_id=active_user.id,
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(active_user)),
        )

        assert response.status_code == 200

    def test_non_owner_denied_private_document(
        self,
        doc_client: TestClient,
        active_user: User,
        hr_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            active_user.id,
            visibility=DocumentVisibility.PRIVATE,
            owner_id=active_user.id,
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(hr_user)),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


# ---------------------------------------------------------------------------
# PUBLIC visibility
# ---------------------------------------------------------------------------

class TestPublicVisibilityIntegration:
    def test_any_role_can_read_public_document(
        self,
        doc_client: TestClient,
        active_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            active_user.id,
            visibility=DocumentVisibility.PUBLIC,
            owner_id=active_user.id,
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(active_user)),
        )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# RESTRICTED visibility
# ---------------------------------------------------------------------------

class TestRestrictedVisibilityIntegration:
    def test_authorized_role_can_read_restricted_document(
        self,
        doc_client: TestClient,
        hr_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            hr_user.id,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR", "Finance"],
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(hr_user)),
        )

        assert response.status_code == 200

    def test_unauthorized_role_denied_restricted_document(
        self,
        doc_client: TestClient,
        active_user: User,
        hr_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            hr_user.id,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(active_user)),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE

    def test_no_allowed_roles_denies_everyone(
        self,
        doc_client: TestClient,
        hr_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            hr_user.id,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=[],
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(hr_user)),
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# PRIVATE visibility
# ---------------------------------------------------------------------------

class TestPrivateVisibilityIntegration:
    def test_non_owner_denied_private_document(
        self,
        doc_client: TestClient,
        finance_user: User,
        hr_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            hr_user.id,
            visibility=DocumentVisibility.PRIVATE,
            owner_id=hr_user.id,
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(finance_user)),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


# ---------------------------------------------------------------------------
# Malformed metadata handled safely
# ---------------------------------------------------------------------------

class TestMalformedMetadataIntegration:
    def test_unknown_visibility_value_denies_non_admin(
        self,
        doc_client: TestClient,
        active_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            active_user.id,
            visibility=DocumentVisibility.PUBLIC,
        )
        doc.visibility = "top-secret"
        db_session.add(doc)
        db_session.commit()

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(active_user)),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE

    def test_unknown_role_in_allowed_roles_is_ignored(
        self,
        doc_client: TestClient,
        hr_user: User,
        db_session: Session,
    ) -> None:
        doc = _make_document(
            db_session,
            hr_user.id,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR", "bogus_role", "Confidential"],
        )

        response = doc_client.get(
            _document_url(doc.id),
            headers=bearer_headers(access_token_for(hr_user)),
        )

        # "HR" is valid → access granted
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Not found returns 404, not 403
# ---------------------------------------------------------------------------

class TestNotFoundBeforeAuthorization:
    def test_nonexistent_document_returns_404(
        self,
        doc_client: TestClient,
        active_user: User,
    ) -> None:
        missing_id = uuid.uuid4()
        response = doc_client.get(
            _document_url(missing_id),
            headers=bearer_headers(access_token_for(active_user)),
        )

        assert response.status_code == 404
