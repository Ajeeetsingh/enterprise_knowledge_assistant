"""Conversation-aware chat orchestration (Phase 6.6).

Coordinates conversation persistence, context assembly, and the existing
RAG service without modifying retrieval, ranking, or authorization logic.

Flow:
    1. Persist the user message.
    2. Build conversation context via ``ContextBuilder``.
    3. Call ``RagService.answer_question`` with ``current_question`` for retrieval
       and formatted history for LLM prompt injection only.
    4. Persist the assistant message on success.

If RAG fails after step 1, the user message remains stored and the error
propagates through existing global exception handling.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.db.models.message import Message
from app.db.models.user import User
from app.rag.answer_generator import UNAVAILABLE_MESSAGE
from app.rag.types import Citation, QueryResponse
from app.services.context_builder import (
    DEFAULT_CONTEXT_WINDOW,
    MAX_CONTEXT_CHARACTERS,
    ContextBuilder,
    ConversationContext,
)
from app.services.conversation_service import ConversationService

if TYPE_CHECKING:
    from app.services.rag_service import RagService


@dataclass(frozen=True)
class ConversationChatResult:
    """Outcome of a successful conversation-aware chat turn.

    Attributes:
        conversation_id: The conversation the turn belongs to.
        answer: Generated answer text from the RAG engine.
        citations: Serialized citation objects for API persistence.
        confidence_score: Overall answer confidence from the RAG engine.
        message: Status message from the RAG engine.
    """

    conversation_id: uuid.UUID
    answer: str
    citations: list[dict[str, Any]]
    confidence_score: float
    message: str


class ConversationChatService:
    """Orchestrates conversation memory with the existing RAG pipeline.

    This service owns the conversation/RAG integration boundary.  It does not
    implement retrieval, document authorization, or vector search — those
    remain in ``RagService`` and the route-layer authorization helpers.
    """

    def __init__(self, conversation_service: ConversationService) -> None:
        self._conversation_service = conversation_service

    def ask_question(
        self,
        user: User,
        conversation_id: uuid.UUID,
        question: str,
        role_name: str,
        rag_service: RagService,
        authorized_sources: frozenset[str] | None,
    ) -> ConversationChatResult:
        """Process a conversation turn and return the generated answer.

        Args:
            user: Authenticated user who owns the conversation.
            conversation_id: Target conversation primary key.
            question: Current natural-language question.
            role_name: Primary role forwarded to the RAG engine for category RBAC.
            rag_service: Existing RAG integration service.
            authorized_sources: Document-level authorized source filenames,
                computed by the retrieval authorization layer before this call.

        Returns:
            ``ConversationChatResult`` with answer metadata on success.

        Raises:
            ConversationNotFoundError: When the conversation does not exist.
            ConversationAccessDeniedError: When the user does not own the
                conversation.
            MessageValidationError: When *question* is empty or blank.
            RagInitializationError: When the RAG engine cannot initialize.
            RagRetrievalError: When retrieval fails after the user message
                was persisted.
        """
        user_message = self._conversation_service.add_user_message(
            user,
            conversation_id,
            question,
        )

        context = self._build_context_after_user_message(
            user,
            conversation_id,
            question,
            stored_user_message_id=user_message.id,
        )

        query_response = rag_service.answer_question(
            context.current_question,
            role_name,
            authorized_sources,
            conversation_history=ContextBuilder.format_history(context.history_messages),
        )

        assistant_content = resolve_assistant_content(query_response)
        citations = _serialize_citations(query_response.citations)
        self._conversation_service.add_assistant_message(
            user,
            conversation_id,
            content=assistant_content,
            citations=citations,
            confidence_score=query_response.confidence_score,
        )

        return ConversationChatResult(
            conversation_id=conversation_id,
            answer=assistant_content,
            citations=citations,
            confidence_score=query_response.confidence_score,
            message=query_response.message,
        )

    def _build_context_after_user_message(
        self,
        user: User,
        conversation_id: uuid.UUID,
        question: str,
        *,
        stored_user_message_id: uuid.UUID,
    ) -> ConversationContext:
        """Build context using prior history only.

        The current user message is persisted before context assembly.  The
        most recently stored user turn is excluded from the history window so
        it appears only in the ``Current question`` section of the query.
        """
        recent = self._conversation_service.get_recent_messages(
            user,
            conversation_id,
            DEFAULT_CONTEXT_WINDOW,
        )
        history = _history_excluding_stored_turn(recent, stored_user_message_id)
        clean_question = question.strip()
        return ContextBuilder.build(
            clean_question,
            history,
            max_chars=MAX_CONTEXT_CHARACTERS,
        )


def resolve_assistant_content(query_response: QueryResponse) -> str:
    """Return non-blank assistant content suitable for conversation persistence.

    The RAG engine may leave ``answer`` empty while providing a user-facing
    explanation in ``message`` (for example category-level RBAC denials).
    """
    answer = query_response.answer.strip()
    if answer:
        return answer

    message = query_response.message.strip()
    if message:
        return message

    return UNAVAILABLE_MESSAGE


def _history_excluding_stored_turn(
    recent_messages: list[Message],
    stored_user_message_id: uuid.UUID,
) -> list[Message]:
    """Drop the just-persisted user message from the history window."""
    return [message for message in recent_messages if message.id != stored_user_message_id]


def _serialize_citations(citations: list[Citation]) -> list[dict[str, Any]]:
    """Convert native RAG citations into JSON-serializable dicts."""
    return [
        {
            "source": citation.source,
            "excerpt": citation.excerpt,
            "confidence": citation.confidence,
            "page": getattr(citation, "page", None),
        }
        for citation in citations
    ]


def build_conversation_chat_service(db: Session) -> ConversationChatService:
    """Construct a ``ConversationChatService`` bound to *db*."""
    from app.services.conversation_service import build_conversation_service

    return ConversationChatService(build_conversation_service(db))
