"""Unit tests for conversation API mappers (Phase 6.5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.db.models.message import MessageRole
from app.mappers.conversations import (
    map_to_conversation_response,
    map_to_delete_response,
    map_to_history_response,
    map_to_list_response,
    map_to_message_response,
)


class _FakeConversation:
    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.title = "HR Questions"
        self.created_at = datetime(2026, 6, 20, 10, 30, 0)
        self.updated_at = datetime(2026, 6, 20, 10, 35, 0)


class _FakeMessage:
    def __init__(
        self,
        *,
        role: str = MessageRole.USER,
        content: str = "Hello",
        citations: list | None = None,
        confidence_score: float | None = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.role = role
        self.content = content
        self._citations = citations or []
        self.confidence_score = confidence_score
        self.created_at = datetime(2026, 6, 20, 10, 31, 0)

    @property
    def citations(self) -> list:
        return self._citations


def test_map_to_conversation_response_excludes_internal_fields() -> None:
    conversation = _FakeConversation()
    response = map_to_conversation_response(conversation)
    payload = response.model_dump()
    assert set(payload.keys()) == {"id", "title", "created_at", "updated_at"}
    assert payload["title"] == "HR Questions"


def test_map_to_message_response_includes_public_fields() -> None:
    message = _FakeMessage(
        role=MessageRole.ASSISTANT,
        content="16 weeks of paid leave.",
        citations=[{"source": "handbook.pdf"}],
        confidence_score=0.92,
    )
    response = map_to_message_response(message)
    payload = response.model_dump()
    assert set(payload.keys()) == {
        "id",
        "role",
        "content",
        "citations",
        "confidence_score",
        "created_at",
    }
    assert payload["role"] == MessageRole.ASSISTANT
    assert payload["citations"] == [{"source": "handbook.pdf"}]
    assert payload["confidence_score"] == 0.92


def test_map_to_list_response() -> None:
    conversations = [_FakeConversation(), _FakeConversation()]
    response = map_to_list_response(conversations, total=10)
    assert response.total == 10
    assert len(response.items) == 2


def test_map_to_history_response_preserves_order() -> None:
    messages = [
        _FakeMessage(content="first"),
        _FakeMessage(content="second"),
    ]
    response = map_to_history_response(messages)
    assert [item.content for item in response.items] == ["first", "second"]


def test_map_to_delete_response() -> None:
    conversation_id = uuid.uuid4()
    response = map_to_delete_response(conversation_id)
    assert response.id == conversation_id
    assert "deleted" in response.message.lower()
