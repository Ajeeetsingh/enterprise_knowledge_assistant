"""Unit tests for PromptBuilder."""

from __future__ import annotations

from app.llm.prompt_builder import PromptBuilder
from app.rag.types import RetrievalResult


def _chunk(
    *,
    content: str = "Singapore (HQ) is the group headquarters.",
    source: str = "company_overview.pdf",
    page: int | None = 9,
) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="executive",
        confidence=0.82,
        chunk_id="chunk-1",
        page_number=page,
    )


class TestPromptBuilder:
    def test_includes_retrieved_chunks_with_page_metadata(self) -> None:
        prompt = PromptBuilder().build(
            "What is the company headquarters?",
            [_chunk()],
        )

        assert "Singapore (HQ)" in prompt.user
        assert "company_overview.pdf" in prompt.user
        assert "page 9" in prompt.user
        assert prompt.messages[0]["role"] == "system"
        assert prompt.messages[1]["role"] == "user"

    def test_includes_current_question_only(self) -> None:
        prompt = PromptBuilder().build(
            "What is the company headquarters?",
            [_chunk()],
        )

        assert "Current question: What is the company headquarters?" in prompt.user

    def test_includes_conversation_history_when_provided(self) -> None:
        history = (
            "Conversation context:\n"
            "User: What offices do we have?\n"
            "Assistant: We operate in Singapore and London."
        )
        prompt = PromptBuilder().build(
            "Which one is HQ?",
            [_chunk()],
            conversation_history=history,
        )

        assert history in prompt.user
        assert "for context only" in prompt.user

    def test_empty_retrieval_shows_placeholder(self) -> None:
        prompt = PromptBuilder().build("Any question?", [])

        assert "(No document excerpts retrieved.)" in prompt.user

    def test_total_length_counts_system_and_user(self) -> None:
        prompt = PromptBuilder().build("Question?", [_chunk()])

        assert prompt.total_length == len(prompt.system) + len(prompt.user)
