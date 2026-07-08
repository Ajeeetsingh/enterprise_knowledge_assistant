"""Unit tests for LLM provider factory."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.llm.exceptions import LLMProviderNotConfiguredError
from app.llm.factory import create_llm_provider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.openai import OpenAIProvider


def test_none_provider_returns_none() -> None:
    settings = Settings(llm_provider="none")

    assert create_llm_provider(settings) is None


def test_groq_provider_requires_api_key_when_fallback_disabled() -> None:
    settings = Settings(
        llm_provider="groq",
        groq_api_key=None,
        llm_fallback_enabled=False,
    )

    with pytest.raises(LLMProviderNotConfiguredError, match="GROQ_API_KEY"):
        create_llm_provider(settings)


def test_groq_provider_returns_none_without_key_when_fallback_enabled() -> None:
    settings = Settings(
        llm_provider="groq",
        groq_api_key=None,
        llm_fallback_enabled=True,
    )

    assert create_llm_provider(settings) is None


def test_groq_provider_created_with_api_key() -> None:
    settings = Settings(
        llm_provider="groq",
        groq_api_key="test-key",
        llm_model="llama-3.3-70b-versatile",
    )

    provider = create_llm_provider(settings)

    assert isinstance(provider, GroqProvider)
    assert provider.model_name == "llama-3.3-70b-versatile"


def test_openai_placeholder_created_with_api_key() -> None:
    settings = Settings(
        llm_provider="openai",
        openai_api_key="test-key",
        llm_model="gpt-4o-mini",
    )

    provider = create_llm_provider(settings)

    assert isinstance(provider, OpenAIProvider)
    assert provider.model_name == "gpt-4o-mini"


def test_unsupported_provider_raises() -> None:
    settings = Settings(llm_provider="anthropic")

    with pytest.raises(LLMProviderNotConfiguredError, match="Unsupported LLM_PROVIDER"):
        create_llm_provider(settings)
