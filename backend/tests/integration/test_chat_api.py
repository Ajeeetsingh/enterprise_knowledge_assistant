"""Integration tests for POST /api/v1/chat/ask."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import User
from app.dependencies import get_db, get_rag_service_dep
from app.main import app
from app.schemas.chat import QUESTION_MAX_LENGTH
from app.core.exceptions import RagInitializationError, RagRetrievalError
from tests.integration.conftest import access_token_for, bearer_headers

ASK_URL = "/api/v1/chat/ask"

INTERNAL_RESPONSE_FIELDS = {
    "query",
    "role",
    "routed_category",
    "route_confidence",
    "sources_used",
    "access_granted",
}

PUBLIC_RESPONSE_FIELDS = {
    "answer",
    "confidence_score",
    "citations",
    "message",
}


def _fake_query_response() -> SimpleNamespace:
    return SimpleNamespace(
        query="How many annual leaves do employees receive?",
        role="employee",
        routed_category="hr",
        route_confidence=0.9,
        answer="Employees receive 20 annual leave days.",
        sources_used=["hr_policy.txt"],
        citations=[
            SimpleNamespace(
                source="hr_policy.txt",
                excerpt="Annual leave: 20 days per year.",
                confidence=0.88,
            )
        ],
        confidence_score=0.85,
        access_granted=True,
        message="Answer generated from hr_policy.txt.",
    )


@pytest.fixture
def mock_rag_service() -> MagicMock:
    service = MagicMock()
    service.answer_question.return_value = _fake_query_response()
    return service


@pytest.fixture
def chat_client(
    db_session: Session,
    mock_rag_service: MagicMock,
) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rag_service_dep] = lambda: mock_rag_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_authenticated_request_returns_answer_response(
    chat_client: TestClient,
    mock_rag_service: MagicMock,
    active_user: User,
) -> None:
    token = access_token_for(active_user)
    payload = {"question": "How many annual leaves do employees receive?"}

    response = chat_client.post(ASK_URL, headers=bearer_headers(token), json=payload)

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == PUBLIC_RESPONSE_FIELDS
    assert INTERNAL_RESPONSE_FIELDS.isdisjoint(data.keys())
    assert data["answer"] == "Employees receive 20 annual leave days."
    assert data["confidence_score"] == 0.85
    assert data["message"] == "Answer generated from hr_policy.txt."
    assert data["citations"] == [
        {
            "source": "hr_policy.txt",
            "excerpt": "Annual leave: 20 days per year.",
            "confidence": 0.88,
        }
    ]
    mock_rag_service.answer_question.assert_called_once_with(
        payload["question"],
        "Employee",
    )


def test_role_forwarded_for_admin_user(
    chat_client: TestClient,
    mock_rag_service: MagicMock,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)

    response = chat_client.post(
        ASK_URL,
        headers=bearer_headers(token),
        json={"question": "Were there security incidents?"},
    )

    assert response.status_code == 200
    mock_rag_service.answer_question.assert_called_once_with(
        "Were there security incidents?",
        "Admin",
    )


def test_missing_jwt_returns_401(chat_client: TestClient) -> None:
    response = chat_client.post(
        ASK_URL,
        json={"question": "What is the leave policy?"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_invalid_jwt_returns_401(chat_client: TestClient) -> None:
    response = chat_client.post(
        ASK_URL,
        headers=bearer_headers("invalid-token"),
        json={"question": "What is the leave policy?"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials."


def test_initialization_failure_returns_503(
    chat_client: TestClient,
    mock_rag_service: MagicMock,
    active_user: User,
) -> None:
    mock_rag_service.answer_question.side_effect = RagInitializationError(
        "Knowledge base data directory is not available."
    )
    token = access_token_for(active_user)

    response = chat_client.post(
        ASK_URL,
        headers=bearer_headers(token),
        json={"question": "What is the leave policy?"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Knowledge service is temporarily unavailable."


def test_retrieval_failure_returns_500(
    chat_client: TestClient,
    mock_rag_service: MagicMock,
    active_user: User,
) -> None:
    mock_rag_service.answer_question.side_effect = RagRetrievalError(
        "Knowledge retrieval failed."
    )
    token = access_token_for(active_user)

    response = chat_client.post(
        ASK_URL,
        headers=bearer_headers(token),
        json={"question": "What is the leave policy?"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to process knowledge request."


def test_empty_question_returns_422(
    chat_client: TestClient,
    active_user: User,
) -> None:
    token = access_token_for(active_user)

    response = chat_client.post(
        ASK_URL,
        headers=bearer_headers(token),
        json={"question": "   "},
    )

    assert response.status_code == 422


def test_missing_question_returns_422(
    chat_client: TestClient,
    active_user: User,
) -> None:
    token = access_token_for(active_user)

    response = chat_client.post(
        ASK_URL,
        headers=bearer_headers(token),
        json={},
    )

    assert response.status_code == 422


def test_question_exceeding_max_length_returns_422(
    chat_client: TestClient,
    active_user: User,
) -> None:
    token = access_token_for(active_user)

    response = chat_client.post(
        ASK_URL,
        headers=bearer_headers(token),
        json={"question": "a" * (QUESTION_MAX_LENGTH + 1)},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid request."


def test_chat_route_has_no_manual_rag_exception_handling() -> None:
    from pathlib import Path

    chat_source = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "api"
        / "v1"
        / "chat.py"
    ).read_text(encoding="utf-8")

    assert "RagInitializationError" not in chat_source
    assert "RagRetrievalError" not in chat_source
    assert "except " not in chat_source


def test_openapi_includes_chat_models(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]

    assert "ChatAskRequest" in schemas
    assert "AnswerResponse" in schemas
    assert "CitationResponse" in schemas
    assert "ErrorResponse" in schemas

    ask_op = response.json()["paths"]["/api/v1/chat/ask"]["post"]
    assert ask_op["summary"] == "Ask a knowledge question"
    assert "200" in ask_op["responses"]
    assert ask_op["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("AnswerResponse")
