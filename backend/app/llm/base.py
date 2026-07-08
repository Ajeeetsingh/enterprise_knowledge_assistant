"""Abstract LLM provider interface."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.llm.types import LLMGenerationRequest, LLMGenerationResult


class LLMProvider(ABC):
    """Provider-agnostic interface for retrieval-augmented answer generation.

    Concrete providers (Groq, OpenAI, Gemini, Ollama) implement ``generate``.
    Streaming can be added later via ``stream`` without changing callers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short provider identifier (e.g. ``groq``)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Configured model slug for this provider."""

    @abstractmethod
    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        """Generate an answer from the assembled prompt and retrieved context."""

    def generate_sync(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        """Synchronous wrapper used by the existing RAG engine."""
        return asyncio.run(self.generate(request))

    async def stream(self, request: LLMGenerationRequest) -> AsyncIterator[str]:
        """Stream answer tokens.

        Default implementation signals that streaming is not yet available.
        Providers may override when streaming is implemented.
        """
        raise NotImplementedError(
            f"Streaming is not implemented for provider '{self.provider_name}'."
        )
        yield ""  # pragma: no cover — makes this an async generator for type checkers
