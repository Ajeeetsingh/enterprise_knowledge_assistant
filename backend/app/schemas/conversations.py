"""Pydantic models for the conversation management API (Phase 6.5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models.message import MessageRole
from app.services.conversation_service import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT, MAX_TITLE_LENGTH


class ConversationCreateRequest(BaseModel):
    """Request body for creating a new conversation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"title": "HR Questions"},
                {"title": None},
            ]
        }
    )

    title: str | None = Field(
        default=None,
        max_length=MAX_TITLE_LENGTH,
        description="Optional human-readable title for the conversation.",
        examples=["HR Questions"],
    )


class ConversationUpdateRequest(BaseModel):
    """Request body for renaming an existing conversation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"title": "Updated HR Questions"},
            ]
        }
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=MAX_TITLE_LENGTH,
        description="New human-readable title for the conversation.",
        examples=["Updated HR Questions"],
    )

    @field_validator("title")
    @classmethod
    def strip_and_validate_title(cls, value: str) -> str:
        """Trim whitespace and reject blank titles."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Conversation title must not be empty or blank.")
        if len(stripped) > MAX_TITLE_LENGTH:
            raise ValueError(
                f"Conversation title must not exceed {MAX_TITLE_LENGTH} characters "
                f"(got {len(stripped)})."
            )
        return stripped


class ConversationResponse(BaseModel):
    """Public representation of a single conversation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "title": "HR Questions",
                    "created_at": "2026-06-20T10:30:00Z",
                    "updated_at": "2026-06-20T10:35:00Z",
                }
            ]
        }
    )

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier for the conversation.",
    )
    title: str | None = Field(
        default=None,
        description="Optional human-readable title.",
        examples=["HR Questions"],
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the conversation was created.",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp of the most recent conversation activity.",
    )


class ConversationListResponse(BaseModel):
    """Paginated list of conversations owned by the authenticated user."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "title": "HR Questions",
                            "created_at": "2026-06-20T10:30:00Z",
                            "updated_at": "2026-06-20T10:35:00Z",
                        }
                    ],
                    "total": 25,
                }
            ]
        }
    )

    items: list[ConversationResponse] = Field(
        default_factory=list,
        description="Page of conversations for the authenticated user.",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of conversations owned by the user.",
        examples=[25],
    )


class MessageResponse(BaseModel):
    """Public representation of a single conversation message."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "role": "user",
                    "content": "What is our maternity leave policy?",
                    "citations": [],
                    "confidence_score": None,
                    "created_at": "2026-06-20T10:31:00Z",
                }
            ]
        }
    )

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier for the message.",
    )
    role: MessageRole = Field(
        ...,
        description="Role of the message author (user, assistant, or system).",
        examples=[MessageRole.USER],
    )
    content: str = Field(
        ...,
        description="Text content of the message.",
    )
    citations: list[Any] = Field(
        default_factory=list,
        description="Structured citation objects for assistant messages.",
    )
    confidence_score: float | None = Field(
        default=None,
        description="Optional RAG confidence score for assistant messages.",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the message was created.",
    )


class ConversationHistoryResponse(BaseModel):
    """Ordered conversation history for a single conversation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                            "role": "user",
                            "content": "What is our maternity leave policy?",
                            "citations": [],
                            "confidence_score": None,
                            "created_at": "2026-06-20T10:31:00Z",
                        }
                    ]
                }
            ]
        }
    )

    items: list[MessageResponse] = Field(
        default_factory=list,
        description="Messages ordered oldest to newest.",
    )


class ConversationDeleteResponse(BaseModel):
    """Response after a successful conversation deletion."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "message": "Conversation deleted successfully.",
                }
            ]
        }
    )

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier of the deleted conversation.",
    )
    message: str = Field(
        ...,
        description="Human-readable confirmation of the deletion.",
        examples=["Conversation deleted successfully."],
    )


# Re-export list pagination limits for OpenAPI query parameter documentation.
__all__ = [
    "DEFAULT_LIST_LIMIT",
    "MAX_LIST_LIMIT",
    "ConversationCreateRequest",
    "ConversationUpdateRequest",
    "ConversationDeleteResponse",
    "ConversationHistoryResponse",
    "ConversationListResponse",
    "ConversationResponse",
    "MessageResponse",
]
