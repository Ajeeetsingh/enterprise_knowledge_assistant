"""Map internal RAG responses to public chat API models."""

from __future__ import annotations

from typing import Protocol

from app.schemas.chat import AnswerResponse, CitationResponse


class _CitationLike(Protocol):
    source: str
    excerpt: str
    confidence: float


class _QueryResponseLike(Protocol):
    answer: str
    confidence_score: float
    citations: list[_CitationLike]
    message: str


def map_to_answer_response(query_response: _QueryResponseLike) -> AnswerResponse:
    """Convert a native RAG query result into the public API contract."""
    return AnswerResponse(
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
