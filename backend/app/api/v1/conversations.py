"""Conversation management API endpoints (Phase 6.5)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.auth.security import get_current_user
from app.db.models import User
from app.dependencies import get_conversation_service
from app.mappers.conversations import (
    map_to_conversation_response,
    map_to_delete_response,
    map_to_history_response,
    map_to_list_response,
)
from app.schemas.conversations import (
    DEFAULT_LIST_LIMIT,
    MAX_LIST_LIMIT,
    ConversationCreateRequest,
    ConversationUpdateRequest,
    ConversationDeleteResponse,
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationResponse,
)
from app.schemas.errors import ErrorResponse
from app.services.conversation_service import ConversationService

router = APIRouter()

_CONVERSATION_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Authenticated user does not own this conversation.",
    },
    404: {
        "model": ErrorResponse,
        "description": "Conversation not found.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Invalid conversation data.",
    },
}


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation",
    description=(
        "Create a new chat conversation owned by the authenticated user. "
        "An optional title may be provided."
    ),
    responses=_CONVERSATION_ERROR_RESPONSES,
)
def create_conversation(
    body: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """Create a conversation for the authenticated user."""
    conversation = conversation_service.create_conversation(
        current_user,
        title=body.title,
    )
    return map_to_conversation_response(conversation)


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List conversations",
    description=(
        "Return a paginated list of conversations owned by the authenticated user, "
        "ordered by most recent activity first."
    ),
    responses=_CONVERSATION_ERROR_RESPONSES,
)
def list_conversations(
    limit: int = Query(
        DEFAULT_LIST_LIMIT,
        ge=1,
        le=MAX_LIST_LIMIT,
        description="Maximum number of conversations to return.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of conversations to skip before returning results.",
    ),
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    """List conversations for the authenticated user."""
    conversations, total = conversation_service.list_conversations(
        current_user,
        limit=limit,
        offset=offset,
    )
    return map_to_list_response(conversations, total=total)


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get a conversation",
    description=(
        "Return a single conversation by ID. Only the conversation owner may access it."
    ),
    responses=_CONVERSATION_ERROR_RESPONSES,
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """Return a single owned conversation."""
    conversation = conversation_service.get_conversation(current_user, conversation_id)
    return map_to_conversation_response(conversation)


@router.put(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Rename a conversation",
    description=(
        "Update the title of an existing conversation. "
        "Only the conversation owner may rename it."
    ),
    responses=_CONVERSATION_ERROR_RESPONSES,
)
def rename_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """Rename an owned conversation.

    Persisted conversation CRUD audit events are not recorded here because
    Phase 7 audit integration covers chat workflows only
    (``chat_audit_integration``), not conversation metadata changes.
    """
    conversation = conversation_service.rename_conversation(
        current_user,
        conversation_id,
        body.title,
    )
    return map_to_conversation_response(conversation)


@router.delete(
    "/{conversation_id}",
    response_model=ConversationDeleteResponse,
    summary="Delete a conversation",
    description=(
        "Delete a conversation and all of its messages. "
        "Only the conversation owner may delete it."
    ),
    responses=_CONVERSATION_ERROR_RESPONSES,
)
def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDeleteResponse:
    """Delete an owned conversation and cascade-delete its messages."""
    conversation_service.delete_conversation(current_user, conversation_id)
    return map_to_delete_response(conversation_id)


@router.get(
    "/{conversation_id}/messages",
    response_model=ConversationHistoryResponse,
    summary="Get conversation history",
    description=(
        "Return all messages for a conversation ordered oldest to newest. "
        "Only the conversation owner may access the history."
    ),
    responses=_CONVERSATION_ERROR_RESPONSES,
)
def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationHistoryResponse:
    """Return ordered message history for an owned conversation."""
    messages = conversation_service.get_conversation_history(
        current_user,
        conversation_id,
    )
    return map_to_history_response(messages)
