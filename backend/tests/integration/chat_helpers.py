"""Shared helpers for conversation-aware chat integration tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.integration.conftest import bearer_headers

CONVERSATIONS_URL = "/api/v1/conversations"
ASK_URL = "/api/v1/chat/ask"


def create_conversation(
    client: TestClient,
    token: str,
    *,
    title: str = "Test Conversation",
) -> str:
    """Create a conversation and return its ID."""
    response = client.post(
        CONVERSATIONS_URL,
        headers=bearer_headers(token),
        json={"title": title},
    )
    assert response.status_code == 201
    return response.json()["id"]


def ask_payload(conversation_id: str, question: str) -> dict[str, str]:
    """Build a conversation-aware chat request body."""
    return {
        "conversation_id": conversation_id,
        "question": question,
    }
