"""Unit tests for GroqProvider."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.llm.exceptions import LLMGenerationError, LLMProviderNotConfiguredError
from app.llm.prompt_builder import PromptBuilder
from app.llm.providers.groq import GroqProvider
from app.llm.types import LLMGenerationRequest
from app.rag.types import RetrievalResult


def _request() -> LLMGenerationRequest:
    chunk = RetrievalResult(
        content="Singapore (HQ) is the headquarters.",
        source="company_overview.pdf",
        category="executive",
        confidence=0.9,
        chunk_id="c1",
        page_number=9,
    )
    prompt = PromptBuilder().build("Where is HQ?", [chunk])
    return LLMGenerationRequest(
        question="Where is HQ?",
        retrieved_chunks=[chunk],
        conversation_history=None,
        prompt=prompt,
    )


class TestGroqProvider:
    def test_requires_api_key(self) -> None:
        with pytest.raises(LLMProviderNotConfiguredError, match="GROQ_API_KEY"):
            GroqProvider(
                api_key=None,
                model="llama-3.3-70b-versatile",
                temperature=0.1,
                max_tokens=256,
                timeout_seconds=30.0,
            )

    def test_generate_returns_answer_and_token_usage(self) -> None:
        provider = GroqProvider(
            api_key="test-key",
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=256,
            timeout_seconds=30.0,
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "id": "chatcmpl-test",
            "choices": [{"message": {"content": "The headquarters is in Singapore."}}],
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 18,
                "total_tokens": 138,
            },
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.llm.providers.groq.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.run(provider.generate(_request()))

        assert result.answer == "The headquarters is in Singapore."
        assert result.provider_name == "groq"
        assert result.model == "llama-3.3-70b-versatile"
        assert result.token_usage is not None
        assert result.token_usage.total_tokens == 138
        mock_client.post.assert_awaited_once()

    def test_generate_raises_on_http_error(self) -> None:
        provider = GroqProvider(
            api_key="test-key",
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=256,
            timeout_seconds=30.0,
        )

        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(401, request=request, text="Unauthorized")
        http_error = httpx.HTTPStatusError("Unauthorized", request=request, response=response)

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = http_error

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.llm.providers.groq.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(LLMGenerationError, match="HTTP 401"):
                asyncio.run(provider.generate(_request()))
