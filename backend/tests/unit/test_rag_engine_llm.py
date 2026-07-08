"""Unit tests for EnterpriseRAG LLM generation path."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.llm.exceptions import LLMGenerationError
from app.llm.prompt_builder import PromptBuilder
from app.llm.types import LLMGenerationResult, TokenUsage
from app.rag.engine import EnterpriseRAG
from app.rag.types import RetrievalResult


def _retrieval_hit() -> RetrievalResult:
    return RetrievalResult(
        content="Remote employees may work up to three days per week.",
        source="remote_work_policy.pdf",
        category="hr",
        confidence=0.77,
        chunk_id="chunk-1",
        page_number=2,
    )


class _FakeLLMProvider:
    provider_name = "groq"
    model_name = "llama-3.3-70b-versatile"

    def __init__(self, *, answer: str = "Up to three days per week.", fail: bool = False) -> None:
        self._answer = answer
        self._fail = fail
        self.last_request = None

    def generate_sync(self, request):
        self.last_request = request
        if self._fail:
            raise LLMGenerationError("provider unavailable")
        return LLMGenerationResult(
            answer=self._answer,
            provider_name=self.provider_name,
            model=self.model_name,
            latency_ms=42.0,
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


@pytest.fixture
def rag_with_llm() -> EnterpriseRAG:
    engine = EnterpriseRAG(
        vector_store=MagicMock(),
        llm_provider=_FakeLLMProvider(),
        prompt_builder=PromptBuilder(),
        llm_fallback_enabled=True,
    )
    engine._initialized = True
    engine._search = MagicMock(return_value=[_retrieval_hit()])
    return engine


class TestEnterpriseRAGLLMPath:
    def test_uses_llm_provider_for_answer(self, rag_with_llm: EnterpriseRAG) -> None:
        response = rag_with_llm.query("What is the remote work policy?", "employee")

        assert response.answer == "Up to three days per week."
        assert response.confidence_score == 0.77
        assert response.sources_used == ["remote_work_policy.pdf"]
        assert len(response.citations) == 1
        assert response.citations[0].page == 2

    def test_conversation_history_injected_into_prompt_only(
        self,
        rag_with_llm: EnterpriseRAG,
    ) -> None:
        history = "Conversation context:\nUser: Tell me about remote work."

        rag_with_llm.query(
            "How many days?",
            "employee",
            conversation_history=history,
        )

        provider = rag_with_llm._llm_provider
        assert provider.last_request is not None
        assert provider.last_request.question == "How many days?"
        assert history in provider.last_request.prompt.user

        search_args, search_kwargs = rag_with_llm._search.call_args
        assert search_args[0] == "How many days?"
        assert history not in search_args[0]

    def test_falls_back_to_answer_generator_when_llm_fails(
        self,
    ) -> None:
        engine = EnterpriseRAG(
            vector_store=MagicMock(),
            llm_provider=_FakeLLMProvider(fail=True),
            llm_fallback_enabled=True,
        )
        engine._initialized = True
        engine._search = MagicMock(return_value=[_retrieval_hit()])
        engine.answer_generator.generate = MagicMock(
            return_value=MagicMock(
                answer="Fallback answer.",
                sources_used=["remote_work_policy.pdf"],
                confidence_score=0.77,
            )
        )

        response = engine.query("What is the remote work policy?", "employee")

        assert response.answer == "Fallback answer."
        engine.answer_generator.generate.assert_called_once()
