"""OpenAI LLM provider placeholder."""

from __future__ import annotations

from app.llm.base import LLMProvider
from app.llm.exceptions import LLMProviderNotImplementedError
from app.llm.types import LLMGenerationRequest, LLMGenerationResult


class OpenAIProvider(LLMProvider):
    """Placeholder for OpenAI Chat Completions integration."""

    def __init__(self, *, model: str) -> None:
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        raise LLMProviderNotImplementedError(
            "OpenAIProvider is not implemented yet. Set LLM_PROVIDER=groq or enable "
            "llm_fallback_enabled to use the rule-based AnswerGenerator."
        )
