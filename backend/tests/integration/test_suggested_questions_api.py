"""Integration tests for GET /api/v1/chat/suggested-questions."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Document, User
from app.dependencies import get_db, get_suggested_question_service_dep
from app.main import app
from app.services.suggested_questions import SuggestedQuestion
from tests.integration.conftest import access_token_for, bearer_headers

SUGGESTED_QUESTIONS_URL = "/api/v1/chat/suggested-questions"


def _make_document(
    db_session: Session,
    *,
    uploaded_by: uuid.UUID,
    filename: str,
    visibility: str = "public",
    allowed_roles: list[str] | None = None,
) -> Document:
    document = Document(
        id=uuid.uuid4(),
        filename=filename,
        content_type="application/pdf",
        file_size=1024,
        checksum=uuid.uuid4().hex,
        storage_path=f"documents/{filename}",
        uploaded_by=uploaded_by,
        status="searchable",
        visibility=visibility,
    )
    document.allowed_roles = allowed_roles
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def mock_suggestion_service() -> MagicMock:
    service = MagicMock()
    return service


@pytest.fixture
def suggestions_client(
    db_session: Session,
    mock_suggestion_service: MagicMock,
) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_suggested_question_service_dep] = (
        lambda: mock_suggestion_service
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_requires_authentication(suggestions_client: TestClient) -> None:
    response = suggestions_client.get(SUGGESTED_QUESTIONS_URL)
    assert response.status_code == 401


def test_returns_onboarding_questions_when_pool_is_empty(
    suggestions_client: TestClient,
    mock_suggestion_service: MagicMock,
    active_user: User,
) -> None:
    mock_suggestion_service.get_candidate_pool.return_value = []
    mock_suggestion_service.get_suggestions.return_value = [
        SuggestedQuestion(text="What can this assistant help me with?", source="", document_title=""),
    ]
    token = access_token_for(active_user)

    response = suggestions_client.get(SUGGESTED_QUESTIONS_URL, headers=bearer_headers(token))

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == [
        {"text": "What can this assistant help me with?", "source": None}
    ]
    mock_suggestion_service.get_suggestions.assert_called_once()
    called_args = mock_suggestion_service.get_suggestions.call_args[0]
    assert called_args[0] == frozenset()


def test_returns_document_grounded_questions_for_authorized_public_document(
    suggestions_client: TestClient,
    mock_suggestion_service: MagicMock,
    active_user: User,
    db_session: Session,
) -> None:
    _make_document(
        db_session,
        uploaded_by=active_user.id,
        filename="commercial_paper.pdf",
        visibility="public",
    )
    pool = [
        SuggestedQuestion(
            text="What are the main commercial paper issuers?",
            source="commercial_paper.pdf",
            document_title="Commercial Paper Market Report",
        )
    ]
    mock_suggestion_service.get_candidate_pool.return_value = pool
    mock_suggestion_service.get_suggestions.return_value = pool
    token = access_token_for(active_user)

    response = suggestions_client.get(SUGGESTED_QUESTIONS_URL, headers=bearer_headers(token))

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == [
        {
            "text": "What are the main commercial paper issuers?",
            "source": "commercial_paper.pdf",
        }
    ]
    called_args = mock_suggestion_service.get_suggestions.call_args[0]
    assert called_args[0] == frozenset({"commercial_paper.pdf"})


def test_excludes_sources_the_user_is_not_authorized_to_read(
    suggestions_client: TestClient,
    mock_suggestion_service: MagicMock,
    active_user: User,
    db_session: Session,
) -> None:
    # Employee is not in the allowed_roles list — must be filtered out
    # before the service is asked to pick final suggestions.
    _make_document(
        db_session,
        uploaded_by=active_user.id,
        filename="hr_confidential.pdf",
        visibility="restricted",
        allowed_roles=["HR"],
    )
    pool = [
        SuggestedQuestion(
            text="What is the executive compensation policy?",
            source="hr_confidential.pdf",
            document_title="Confidential HR Report",
        )
    ]
    mock_suggestion_service.get_candidate_pool.return_value = pool
    mock_suggestion_service.get_suggestions.return_value = []
    token = access_token_for(active_user)

    suggestions_client.get(SUGGESTED_QUESTIONS_URL, headers=bearer_headers(token))

    called_args = mock_suggestion_service.get_suggestions.call_args[0]
    assert called_args[0] == frozenset()
