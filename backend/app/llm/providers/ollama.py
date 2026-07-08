"""Ollama LLM provider placeholder."""

from __future__ import annotations

from app.llm.base import LLMProvider
from app.llm.exceptions import LLMProviderNotImplementedError
from app.llm.types import LLMGenerationRequest, LLMGenerationResult


class OllamaProvider(LLMProvider):
    """Placeholder for local Ollama integration."""

    def __init__(self, *, model: str, base_url: str) -> None:
        self._model = model
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        raise LLMProviderNotImplementedError(
            "OllamaProvider is not implemented yet. Set LLM_PROVIDER=groq or enable "
            "llm_fallback_enabled to use the rule-based AnswerGenerator."
        )
