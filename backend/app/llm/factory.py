"""Provider registry and factory."""

from __future__ import annotations

import logging

from app.config import Settings
from app.core.logging import get_logger, log_with_fields
from app.llm.base import LLMProvider
from app.llm.exceptions import LLMProviderNotConfiguredError
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.openai import OpenAIProvider

logger = get_logger(__name__)

_SUPPORTED_PROVIDERS = frozenset({"groq", "openai", "gemini", "ollama", "none", "fallback"})


def _provider_unavailable(
    settings: Settings,
    *,
    provider_name: str,
    reason: str,
) -> LLMProvider | None:
    if settings.llm_fallback_enabled:
        log_with_fields(
            logger,
            logging.WARNING,
            "LLM provider unavailable — AnswerGenerator fallback will be used",
            llm_provider=provider_name,
            reason=reason,
        )
        return None
    raise LLMProviderNotConfiguredError(reason)


def create_llm_provider(settings: Settings) -> LLMProvider | None:
    """Instantiate the configured LLM provider, or ``None`` for fallback-only mode."""
    provider_name = (settings.llm_provider or "none").strip().lower()
    if provider_name in {"none", "fallback", ""}:
        log_with_fields(
            logger,
            logging.INFO,
            "LLM provider disabled — AnswerGenerator fallback will be used",
            llm_provider=provider_name or "none",
        )
        return None

    if provider_name not in _SUPPORTED_PROVIDERS:
        raise LLMProviderNotConfiguredError(
            f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. "
            f"Supported values: {', '.join(sorted(_SUPPORTED_PROVIDERS))}."
        )

    model = settings.llm_model

    if provider_name == "groq":
        if not settings.groq_api_key:
            return _provider_unavailable(
                settings,
                provider_name=provider_name,
                reason="Groq provider requires GROQ_API_KEY to be set.",
            )
        return GroqProvider(
            api_key=settings.groq_api_key,
            model=model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    if provider_name == "openai":
        if not settings.openai_api_key:
            return _provider_unavailable(
                settings,
                provider_name=provider_name,
                reason="OpenAI provider requires OPENAI_API_KEY to be set.",
            )
        return OpenAIProvider(model=model)

    if provider_name == "gemini":
        if not settings.gemini_api_key:
            return _provider_unavailable(
                settings,
                provider_name=provider_name,
                reason="Gemini provider requires GEMINI_API_KEY to be set.",
            )
        return GeminiProvider(model=model)

    if provider_name == "ollama":
        return OllamaProvider(model=model, base_url=settings.ollama_base_url)

    return None
