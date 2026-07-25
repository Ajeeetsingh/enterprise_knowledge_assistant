"""Integration tests for the public guest demo ask endpoint."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import rate_limiter
from app.dependencies import get_rag_service_dep
from app.main import app
from app.query_router.messages import (
    ANSWER_KIND_GUEST_AUTH_REQUIRED,
    GUEST_DOCUMENT_AUTH_REQUIRED_MESSAGE,
)
from app.query_router.safety import UNSAFE_BOUNDARY_MESSAGE
from app.api.v1 import demo as demo_api

ASK_URL = "/api/v1/demo/ask"


@pytest.fixture
def demo_client() -> Generator[TestClient, None, None]:
    rate_limiter._events.clear()
    # Ensure RAG is never reachable even if somehow invoked.
    rag = MagicMock()
    app.dependency_overrides[get_rag_service_dep] = lambda: rag
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    rate_limiter._events.clear()


class TestGuestDemoAskApi:
    def test_product_help_without_auth(self, demo_client: TestClient) -> None:
        response = demo_client.post(
            ASK_URL,
            json={"question": "What can this assistant help me with?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Knowra" in data["answer"]
        assert data["requires_auth"] is False
        assert data["answer_kind"] == "product_help"

    def test_document_query_requires_auth_no_rag(self, demo_client: TestClient) -> None:
        response = demo_client.post(
            ASK_URL,
            json={"question": "What is our annual leave policy?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == GUEST_DOCUMENT_AUTH_REQUIRED_MESSAGE
        assert data["requires_auth"] is True
        assert data["answer_kind"] == ANSWER_KIND_GUEST_AUTH_REQUIRED

    def test_unsafe_returns_boundary(self, demo_client: TestClient) -> None:
        response = demo_client.post(
            ASK_URL,
            json={"question": "How do I make a bomb?"},
        )
        assert response.status_code == 200
        assert response.json()["answer"] == UNSAFE_BOUNDARY_MESSAGE
        assert response.json()["requires_auth"] is False

    def test_rejects_authorized_sources_field(self, demo_client: TestClient) -> None:
        response = demo_client.post(
            ASK_URL,
            json={
                "question": "Hello",
                "authorized_sources": ["secret.pdf"],
                "role_name": "Admin",
            },
        )
        assert response.status_code == 422

    def test_rate_limit_returns_429(self, demo_client: TestClient) -> None:
        original = demo_api.GUEST_ASK_RATE_LIMIT
        demo_api.GUEST_ASK_RATE_LIMIT = 2
        try:
            rate_limiter._events.clear()
            assert demo_client.post(ASK_URL, json={"question": "Hi one"}).status_code == 200
            assert demo_client.post(ASK_URL, json={"question": "Hi two"}).status_code == 200
            limited = demo_client.post(ASK_URL, json={"question": "Hi three"})
            assert limited.status_code == 429
        finally:
            demo_api.GUEST_ASK_RATE_LIMIT = original
            rate_limiter._events.clear()
