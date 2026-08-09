"""Integration tests for Phase 5.3 authorization dependencies."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTHORIZATION_DENIED_MESSAGE
from app.db.models import User
from app.dependencies import get_db, get_document_service_dep
from app.documents.status import DocumentStatus, DocumentUploadResult
from app.main import app
from tests.integration.conftest import access_token_for, bearer_headers

UPLOAD_URL = "/api/v1/documents/upload"
USERS_URL = "/api/v1/users"
ROLES_URL = "/api/v1/roles"


def _fake_upload_result() -> DocumentUploadResult:
    return DocumentUploadResult(
        document_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        filename="policy.txt",
        status=DocumentStatus.SEARCHABLE,
        message="Document 'policy.txt' uploaded and is now searchable.",
    )


@pytest.fixture
def documents_client(
    db_session: Session,
) -> TestClient:
    mock_service = MagicMock()
    mock_service.upload_document.return_value = _fake_upload_result()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_document_service_dep] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_hr_user_can_upload_with_document_create_permission(
    documents_client: TestClient,
    hr_user: User,
) -> None:
    token = access_token_for(hr_user)
    response = documents_client.post(
        UPLOAD_URL,
        headers=bearer_headers(token),
        files={"file": ("policy.txt", b"Annual leave policy", "text/plain")},
        data={"domain_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "policy.txt"


def test_employee_upload_denied_without_document_create(
    documents_client: TestClient,
    active_user: User,
) -> None:
    token = access_token_for(active_user)
    response = documents_client.post(
        UPLOAD_URL,
        headers=bearer_headers(token),
        files={"file": ("policy.txt", b"content", "text/plain")},
        data={"domain_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


def test_admin_user_management_access_granted(
    client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    response = client.get(USERS_URL, headers=bearer_headers(token))

    assert response.status_code == 200


def test_employee_user_management_denied(
    client: TestClient,
    active_user: User,
) -> None:
    token = access_token_for(active_user)
    response = client.get(USERS_URL, headers=bearer_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


def test_employee_role_listing_denied(
    client: TestClient,
    active_user: User,
) -> None:
    token = access_token_for(active_user)
    response = client.get(ROLES_URL, headers=bearer_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


def test_admin_role_listing_granted(
    client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    response = client.get(ROLES_URL, headers=bearer_headers(token))

    assert response.status_code == 200
