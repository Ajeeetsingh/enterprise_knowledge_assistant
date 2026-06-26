"""Map conversation entities to public API models (Phase 6.5)."""

from __future__ import annotations

from typing import Protocol

from app.db.models.message import MessageRole
from app.schemas.conversations import (
    ConversationDeleteResponse,
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)


class _ConversationLike(Protocol):
    id: object
    title: str | None
    created_at: object
    updated_at: object


class _MessageLike(Protocol):
    id: object
    role: str
    content: str

    @property
    def citations(self) -> list: ...

    confidence_score: float | None
    created_at: object


def map_to_conversation_response(
    conversation: _ConversationLike,
) -> ConversationResponse:
    """Convert a conversation entity into the public API contract."""
    return ConversationResponse(
        id=conversation.id,  # type: ignore[arg-type]
        title=conversation.title,
        created_at=conversation.created_at,  # type: ignore[arg-type]
        updated_at=conversation.updated_at,  # type: ignore[arg-type]
    )


def map_to_message_response(message: _MessageLike) -> MessageResponse:
    """Convert a message entity into the public API contract."""
    try:
        role = MessageRole(message.role)
    except ValueError:
        role = MessageRole.USER

    return MessageResponse(
        id=message.id,  # type: ignore[arg-type]
        role=role,
        content=message.content,
        citations=message.citations,
        confidence_score=message.confidence_score,
        created_at=message.created_at,  # type: ignore[arg-type]
    )


def map_to_list_response(
    conversations: list[_ConversationLike],
    *,
    total: int,
) -> ConversationListResponse:
    """Convert a page of conversations into a paginated API response."""
    return ConversationListResponse(
        items=[map_to_conversation_response(item) for item in conversations],
        total=total,
    )


def map_to_history_response(messages: list[_MessageLike]) -> ConversationHistoryResponse:
    """Convert ordered messages into a conversation history response."""
    return ConversationHistoryResponse(
        items=[map_to_message_response(message) for message in messages],
    )


def map_to_delete_response(conversation_id: object) -> ConversationDeleteResponse:
    """Build a delete confirmation response."""
    return ConversationDeleteResponse(
        id=conversation_id,  # type: ignore[arg-type]
        message="Conversation deleted successfully.",
    )
