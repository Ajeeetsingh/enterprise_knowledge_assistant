"""Google Gemini LLM provider placeholder."""

from __future__ import annotations

from app.llm.base import LLMProvider
from app.llm.exceptions import LLMProviderNotImplementedError
from app.llm.types import LLMGenerationRequest, LLMGenerationResult


class GeminiProvider(LLMProvider):
    """Placeholder for Google Gemini integration."""

    def __init__(self, *, model: str) -> None:
        self._model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        raise LLMProviderNotImplementedError(
            "GeminiProvider is not implemented yet. Set LLM_PROVIDER=groq or enable "
            "llm_fallback_enabled to use the rule-based AnswerGenerator."
        )
