"""Integration tests for Phase 5.6 — Audit event generation.

These tests verify that every security-sensitive HTTP action generates an
audit event via ``AuditService.record()``.  We patch ``AuditService.record``
to intercept events without any log capture machinery.

Existing auth/document/RBAC integration tests remain the primary functional
validators; these tests focus solely on the audit event contract.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Generator
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.audit.events import AuditEventType, AuditOutcome
from app.db.models import Document, Role, User
from app.db.models.document import Document as DocumentModel
from app.dependencies import get_db, get_rag_service_dep
from app.documents.visibility import DocumentVisibility
from app.main import app
from tests.constants import TEST_PASSWORD, TEST_PASSWORD_HASH
from tests.integration.conftest import access_token_for, bearer_headers

LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
DOCUMENTS_URL = "/api/v1/documents"
USERS_URL = "/api/v1/users"
ASK_URL = "/api/v1/chat/ask"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recorded_types(mock_record: MagicMock) -> list[AuditEventType]:
    return [c.args[0].event_type for c in mock_record.call_args_list]


def _add_doc(
    db: Session,
    uploader: User,
    *,
    filename: str = "test.txt",
    visibility: DocumentVisibility = DocumentVisibility.PUBLIC,
) -> DocumentModel:
    doc = DocumentModel(
        id=uuid.uuid4(),
        filename=filename,
        content_type="text/plain",
        file_size=10,
        checksum=f"csum-{uuid.uuid4().hex}",
        storage_path=f"docs/{filename}",
        status="searchable",
        uploaded_by=uploader.id,
        owner_id=uploader.id,
        visibility=visibility.value,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag() -> MagicMock:
    from types import SimpleNamespace
    svc = MagicMock()
    svc.answer_question.return_value = SimpleNamespace(
        query="q",
        role="employee",
        routed_category="hr",
        route_confidence=0.9,
        answer="Answer.",
        sources_used=[],
        citations=[],
        confidence_score=0.8,
        access_granted=True,
        message="OK.",
    )
    return svc


@pytest.fixture
def audit_client(
    db_session: Session,
    mock_rag: MagicMock,
) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_rag_service_dep] = lambda: mock_rag
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Authentication audit events
# ---------------------------------------------------------------------------

class TestAuthAuditEvents:
    def test_successful_login_emits_login_success(
        self, audit_client: TestClient, active_user: User
    ) -> None:
        with patch("app.api.v1.auth.AuditService.record") as mock_record:
            response = audit_client.post(
                LOGIN_URL, json={"email": active_user.email, "password": TEST_PASSWORD}
            )
        assert response.status_code == 200
        types = _recorded_types(mock_record)
        assert AuditEventType.AUTH_LOGIN_SUCCESS in types

    def test_failed_login_emits_login_failure(
        self, audit_client: TestClient, active_user: User
    ) -> None:
        with patch("app.api.v1.auth.AuditService.record") as mock_record:
            response = audit_client.post(
                LOGIN_URL,
                json={"email": active_user.email, "password": "wrong-password"},
            )
        assert response.status_code == 401
        types = _recorded_types(mock_record)
        assert AuditEventType.AUTH_LOGIN_FAILURE in types

    def test_logout_emits_logout_event(self, audit_client: TestClient) -> None:
        with patch("app.api.v1.auth.AuditService.record") as mock_record:
            response = audit_client.post(LOGOUT_URL)
        assert response.status_code == 200
        types = _recorded_types(mock_record)
        assert AuditEventType.AUTH_LOGOUT in types

    def test_login_failure_event_has_correct_outcome(
        self, audit_client: TestClient, active_user: User
    ) -> None:
        with patch("app.api.v1.auth.AuditService.record") as mock_record:
            audit_client.post(
                LOGIN_URL, json={"email": "notfound@example.com", "password": "x"}
            )
        events = [c.args[0] for c in mock_record.call_args_list]
        failure_events = [e for e in events if e.event_type == AuditEventType.AUTH_LOGIN_FAILURE]
        assert len(failure_events) >= 1
        assert failure_events[0].outcome == AuditOutcome.FAILURE


# ---------------------------------------------------------------------------
# Permission denied audit events
# ---------------------------------------------------------------------------

class TestPermissionDeniedAuditEvents:
    def test_permission_denied_emits_event(
        self, audit_client: TestClient, active_user: User
    ) -> None:
        """Employee trying to delete a document should emit permission denied."""
        token = access_token_for(active_user)
        with patch("app.auth.dependencies.AuditService.record") as mock_record:
            response = audit_client.delete(
                f"{DOCUMENTS_URL}/{uuid.uuid4()}",
                headers=bearer_headers(token),
            )
        assert response.status_code == 403
        types = _recorded_types(mock_record)
        assert AuditEventType.AUTHZ_PERMISSION_DENIED in types

    def test_permission_denied_event_has_denied_outcome(
        self, audit_client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        with patch("app.auth.dependencies.AuditService.record") as mock_record:
            audit_client.delete(
                f"{DOCUMENTS_URL}/{uuid.uuid4()}",
                headers=bearer_headers(token),
            )
        events = [c.args[0] for c in mock_record.call_args_list]
        denied = [e for e in events if e.event_type == AuditEventType.AUTHZ_PERMISSION_DENIED]
        assert denied[0].outcome == AuditOutcome.DENIED


# ---------------------------------------------------------------------------
# Document access audit events
# ---------------------------------------------------------------------------

class TestDocumentAuditEvents:
    def test_document_read_emits_event(
        self, audit_client: TestClient, active_user: User, db_session: Session
    ) -> None:
        doc = _add_doc(db_session, active_user, visibility=DocumentVisibility.PUBLIC)
        token = access_token_for(active_user)
        with patch("app.api.v1.documents.AuditService.record") as mock_record:
            response = audit_client.get(
                f"{DOCUMENTS_URL}/{doc.id}", headers=bearer_headers(token)
            )
        assert response.status_code == 200
        types = _recorded_types(mock_record)
        assert AuditEventType.DOCUMENT_READ in types

    def test_document_access_denied_emits_event(
        self,
        audit_client: TestClient,
        active_user: User,
        admin_user: User,
        db_session: Session,
    ) -> None:
        """Employee cannot read a private doc owned by admin."""
        doc = _add_doc(
            db_session,
            admin_user,
            visibility=DocumentVisibility.PRIVATE,
        )
        doc.owner_id = admin_user.id
        db_session.commit()

        token = access_token_for(active_user)
        with patch("app.auth.dependencies.AuditService.record") as mock_record:
            response = audit_client.get(
                f"{DOCUMENTS_URL}/{doc.id}", headers=bearer_headers(token)
            )
        assert response.status_code == 403
        types = _recorded_types(mock_record)
        assert AuditEventType.DOCUMENT_ACCESS_DENIED in types

    def test_document_delete_emits_event(
        self, audit_client: TestClient, admin_user: User, db_session: Session
    ) -> None:
        doc = _add_doc(db_session, admin_user, visibility=DocumentVisibility.PUBLIC)
        token = access_token_for(admin_user)
        with patch("app.api.v1.documents.AuditService.record") as mock_record:
            response = audit_client.delete(
                f"{DOCUMENTS_URL}/{doc.id}", headers=bearer_headers(token)
            )
        assert response.status_code in (200, 404)
        types = _recorded_types(mock_record)
        assert AuditEventType.DOCUMENT_DELETE in types


# ---------------------------------------------------------------------------
# User management audit events
# ---------------------------------------------------------------------------

class TestUserManagementAuditEvents:
    def test_user_created_emits_event(
        self, audit_client: TestClient, admin_user: User
    ) -> None:
        token = access_token_for(admin_user)
        with patch("app.api.v1.users.AuditService.record") as mock_record:
            response = audit_client.post(
                USERS_URL,
                headers=bearer_headers(token),
                json={
                    "email": "newaudituser@example.com",
                    "password": TEST_PASSWORD,
                    "full_name": "New User",
                    "username": "newaudituser",
                },
            )
        assert response.status_code == 201
        types = _recorded_types(mock_record)
        assert AuditEventType.ADMIN_USER_CREATED in types

    def test_user_updated_emits_event(
        self, audit_client: TestClient, admin_user: User, active_user: User
    ) -> None:
        token = access_token_for(admin_user)
        with patch("app.api.v1.users.AuditService.record") as mock_record:
            response = audit_client.put(
                f"{USERS_URL}/{active_user.id}",
                headers=bearer_headers(token),
                json={
                    "full_name": "Updated Name",
                    "email": active_user.email,
                    "is_active": True,
                },
            )
        assert response.status_code == 200
        types = _recorded_types(mock_record)
        assert AuditEventType.ADMIN_USER_UPDATED in types

    def test_user_deleted_emits_event(
        self, audit_client: TestClient, admin_user: User, active_user: User
    ) -> None:
        token = access_token_for(admin_user)
        with patch("app.api.v1.users.AuditService.record") as mock_record:
            response = audit_client.delete(
                f"{USERS_URL}/{active_user.id}",
                headers=bearer_headers(token),
            )
        assert response.status_code == 200
        types = _recorded_types(mock_record)
        assert AuditEventType.ADMIN_USER_DELETED in types


# ---------------------------------------------------------------------------
# Role assignment audit events
# ---------------------------------------------------------------------------

class TestRoleAssignmentAuditEvents:
    def test_role_assigned_emits_event(
        self,
        audit_client: TestClient,
        admin_user: User,
        active_user: User,
        employee_role: Role,
    ) -> None:
        token = access_token_for(admin_user)
        with patch("app.api.v1.user_roles.AuditService.record") as mock_record:
            response = audit_client.post(
                f"{USERS_URL}/{active_user.id}/roles",
                headers=bearer_headers(token),
                json={"roles": ["Employee"]},
            )
        assert response.status_code == 200
        types = _recorded_types(mock_record)
        assert AuditEventType.ADMIN_ROLE_ASSIGNED in types

    def test_role_removed_emits_event(
        self,
        audit_client: TestClient,
        admin_user: User,
        active_user: User,
        employee_role: Role,
    ) -> None:
        token = access_token_for(admin_user)
        with patch("app.api.v1.user_roles.AuditService.record") as mock_record:
            response = audit_client.delete(
                f"{USERS_URL}/{active_user.id}/roles/Employee",
                headers=bearer_headers(token),
            )
        assert response.status_code == 200
        types = _recorded_types(mock_record)
        assert AuditEventType.ADMIN_ROLE_REMOVED in types


# ---------------------------------------------------------------------------
# RAG query audit events
# ---------------------------------------------------------------------------

class TestRagQueryAuditEvents:
    def test_rag_query_emits_event(
        self, audit_client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        with patch("app.api.v1.chat.AuditService.record") as mock_record:
            response = audit_client.post(
                ASK_URL,
                headers=bearer_headers(token),
                json={"question": "What is the leave policy?"},
            )
        assert response.status_code == 200
        types = _recorded_types(mock_record)
        assert AuditEventType.RAG_QUERY in types

    def test_rag_query_event_outcome_is_success(
        self, audit_client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        with patch("app.api.v1.chat.AuditService.record") as mock_record:
            audit_client.post(
                ASK_URL,
                headers=bearer_headers(token),
                json={"question": "What is the leave policy?"},
            )
        events = [c.args[0] for c in mock_record.call_args_list]
        rag_events = [e for e in events if e.event_type == AuditEventType.RAG_QUERY]
        assert rag_events[0].outcome == AuditOutcome.SUCCESS
