"""Unit tests for chat response mapping."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.mappers.chat import map_chat_result_to_answer_response, map_to_answer_response
from app.schemas.chat import AnswerResponse, CitationResponse
from app.services.conversation_chat_service import ConversationChatResult

CONVERSATION_ID = uuid.uuid4()

INTERNAL_FIELDS = {
    "query",
    "role",
    "routed_category",
    "route_confidence",
    "sources_used",
    "access_granted",
}


def _sample_query_response() -> SimpleNamespace:
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


def test_map_to_answer_response_maps_all_public_fields() -> None:
    result = map_to_answer_response(
        _sample_query_response(),
        conversation_id=CONVERSATION_ID,
    )

    assert isinstance(result, AnswerResponse)
    assert result.conversation_id == CONVERSATION_ID
    assert result.answer == "Employees receive 20 annual leave days."
    assert result.confidence_score == 0.85
    assert result.message == "Answer generated from hr_policy.txt."
    assert len(result.citations) == 1
    assert result.citations[0] == CitationResponse(
        source="hr_policy.txt",
        excerpt="Annual leave: 20 days per year.",
        confidence=0.88,
    )


def test_map_to_answer_response_excludes_internal_fields() -> None:
    query_response = SimpleNamespace(
        query="hidden query",
        role="admin",
        routed_category="security",
        route_confidence=0.99,
        answer="Answer text.",
        sources_used=["security_logs.json"],
        citations=[],
        confidence_score=0.5,
        access_granted=False,
        message="Access denied.",
    )

    result = map_to_answer_response(query_response, conversation_id=CONVERSATION_ID)
    payload = result.model_dump()

    assert INTERNAL_FIELDS.isdisjoint(payload.keys())
    assert set(payload.keys()) == {
        "conversation_id",
        "answer",
        "confidence_score",
        "citations",
        "message",
    }


def test_map_to_answer_response_handles_empty_citations() -> None:
    query_response = SimpleNamespace(
        query="Unknown topic?",
        role="employee",
        routed_category="general",
        route_confidence=0.1,
        answer="",
        sources_used=[],
        citations=[],
        confidence_score=0.0,
        access_granted=True,
        message="Search completed but no matching chunks were found.",
    )

    result = map_to_answer_response(query_response, conversation_id=CONVERSATION_ID)

    assert result.answer == ""
    assert result.citations == []
    assert result.confidence_score == 0.0


def test_map_chat_result_to_answer_response() -> None:
    result = map_chat_result_to_answer_response(
        ConversationChatResult(
            conversation_id=CONVERSATION_ID,
            answer="Answer text.",
            citations=[
                {
                    "source": "hr_policy.txt",
                    "excerpt": "Excerpt.",
                    "confidence": 0.8,
                }
            ],
            confidence_score=0.75,
            message="Generated.",
        )
    )

    assert result.conversation_id == CONVERSATION_ID
    assert result.answer == "Answer text."
    assert result.citations[0].source == "hr_policy.txt"
