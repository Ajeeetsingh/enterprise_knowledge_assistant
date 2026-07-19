"""Unit tests for conversation title generation."""

from __future__ import annotations

from app.llm.exceptions import LLMGenerationError
from app.llm.types import LLMGenerationResult
from app.services.title_generation import (
    FALLBACK_TITLE,
    generate_conversation_title,
)


class _StubProvider:
    """Minimal ``LLMProvider``-shaped stub for title-generation tests."""

    def __init__(self, *, answer: str | None = None, raises: Exception | None = None) -> None:
        self._answer = answer
        self._raises = raises
        self.calls: list[str] = []

    @property
    def provider_name(self) -> str:
        return "stub"

    @property
    def model_name(self) -> str:
        return "stub-model"

    def generate_sync(self, request) -> LLMGenerationResult:  # noqa: ANN001
        self.calls.append(request.question)
        if self._raises is not None:
            raise self._raises
        return LLMGenerationResult(
            answer=self._answer or "",
            provider_name="stub",
            model="stub-model",
            latency_ms=1.0,
        )


class TestGenerateConversationTitleWithoutProvider:
    def test_empty_question_returns_fallback_title(self) -> None:
        assert generate_conversation_title("   ", None) == FALLBACK_TITLE

    def test_deterministic_title_strips_stopwords_and_title_cases(self) -> None:
        title = generate_conversation_title(
            "What are the main types of commercial paper issuers?", None
        )
        assert title == "Commercial Paper Issuers"

    def test_deterministic_title_drops_leading_question_verb(self) -> None:
        assert generate_conversation_title("Explain Project Phoenix.", None) == "Project Phoenix"

    def test_deterministic_title_preserves_acronym_with_digits(self) -> None:
        title = generate_conversation_title("Summarize FY2026 strategic priorities.", None)
        assert title == "FY2026 Strategic Priorities"

    def test_deterministic_title_caps_at_six_words(self) -> None:
        title = generate_conversation_title(
            "How do Money Market Funds participate in the repo market?", None
        )
        assert len(title.split()) <= 6
        assert title.startswith("Money Market Funds")

    def test_deterministic_title_falls_back_when_all_stopwords(self) -> None:
        # Every token in this question is a stopword — no meaningful content remains.
        title = generate_conversation_title("What is this and how are you?", None)
        assert title
        assert title != ""

    def test_deterministic_title_preserves_acronym_without_digits(self) -> None:
        title = generate_conversation_title("Explain our KYC and AML obligations.", None)
        assert "KYC" in title.split()
        assert "AML" in title.split()


class TestGenerateConversationTitleWithProvider:
    def test_uses_llm_title_when_available(self) -> None:
        provider = _StubProvider(answer="Commercial Paper Issuers")
        title = generate_conversation_title(
            "What are the main types of commercial paper issuers?", provider
        )
        assert title == "Commercial Paper Issuers"
        assert provider.calls == ["What are the main types of commercial paper issuers?"]

    def test_strips_quotes_and_trailing_period_from_llm_response(self) -> None:
        provider = _StubProvider(answer='"Project Phoenix."')
        title = generate_conversation_title("Explain Project Phoenix.", provider)
        assert title == "Project Phoenix"

    def test_strips_title_prefix_from_llm_response(self) -> None:
        provider = _StubProvider(answer="Title: Project Phoenix")
        title = generate_conversation_title("Explain Project Phoenix.", provider)
        assert title == "Project Phoenix"

    def test_truncates_overly_long_llm_response_to_six_words(self) -> None:
        provider = _StubProvider(answer="One Two Three Four Five Six Seven Eight")
        title = generate_conversation_title("Some question.", provider)
        assert title == "One Two Three Four Five Six"

    def test_falls_back_when_llm_raises(self) -> None:
        provider = _StubProvider(raises=LLMGenerationError("boom"))
        title = generate_conversation_title("Explain Project Phoenix.", provider)
        assert title == "Project Phoenix"

    def test_falls_back_when_llm_raises_unexpected_error(self) -> None:
        provider = _StubProvider(raises=RuntimeError("unexpected"))
        title = generate_conversation_title("Explain Project Phoenix.", provider)
        assert title == "Project Phoenix"

    def test_falls_back_when_llm_returns_blank_answer(self) -> None:
        provider = _StubProvider(answer="   ")
        title = generate_conversation_title("Explain Project Phoenix.", provider)
        assert title == "Project Phoenix"

    def test_never_raises_on_provider_failure(self) -> None:
        provider = _StubProvider(raises=ValueError("boom"))
        title = generate_conversation_title("Anything at all?", provider)
        assert isinstance(title, str)
        assert title
