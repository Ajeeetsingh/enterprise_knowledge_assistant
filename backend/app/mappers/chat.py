"""Map internal RAG responses to public chat API models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Protocol

from app.schemas.chat import AnswerResponse, CitationResponse

if TYPE_CHECKING:
    from app.services.conversation_chat_service import ConversationChatResult

if TYPE_CHECKING:
    from app.services.conversation_chat_service import ConversationChatResult


class _CitationLike(Protocol):
    source: str
    excerpt: str
    confidence: float


class _QueryResponseLike(Protocol):
    answer: str
    confidence_score: float
    citations: list[_CitationLike]
    message: str


def map_to_answer_response(
    query_response: _QueryResponseLike,
    *,
    conversation_id: uuid.UUID,
) -> AnswerResponse:
    """Convert a native RAG query result into the public API contract."""
    return AnswerResponse(
        conversation_id=conversation_id,
        answer=query_response.answer,
        confidence_score=query_response.confidence_score,
        citations=[
            CitationResponse(
                source=citation.source,
                excerpt=citation.excerpt,
                confidence=citation.confidence,
            )
            for citation in query_response.citations
        ],
        message=query_response.message,
    )


def map_chat_result_to_answer_response(result: "ConversationChatResult") -> AnswerResponse:
    """Convert a conversation chat result into the public API contract."""
    return AnswerResponse(
        conversation_id=result.conversation_id,
        answer=result.answer,
        confidence_score=result.confidence_score,
        citations=[
            CitationResponse(
                source=citation["source"],
                excerpt=citation["excerpt"],
                confidence=citation["confidence"],
            )
            for citation in result.citations
        ],
        message=result.message,
    )
