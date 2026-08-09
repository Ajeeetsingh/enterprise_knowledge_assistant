"""Types for the LLM generation layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.rag.types import RetrievalResult


@dataclass(frozen=True)
class TokenUsage:
    """Token counts returned by an LLM provider when available."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class BuiltPrompt:
    """Structured prompt payload assembled by ``PromptBuilder``."""

    system: str
    user: str
    messages: list[dict[str, str]] = field(default_factory=list)

    @property
    def total_length(self) -> int:
        return len(self.system) + len(self.user)


@dataclass(frozen=True)
class LLMGenerationRequest:
    """Provider-agnostic generation input."""

    question: str
    retrieved_chunks: list[RetrievalResult]
    conversation_history: str | None
    prompt: BuiltPrompt


@dataclass(frozen=True)
class LLMGenerationResult:
    """Provider-agnostic generation output."""

    answer: str
    provider_name: str
    model: str
    latency_ms: float
    token_usage: TokenUsage | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationOutcome:
    """Unified outcome from LLM or fallback answer synthesis."""

    answer: str
    sources_used: list[str]
    retrieval_confidence: float
    generation_backend: str
    provider_name: str | None = None
    model: str | None = None
    latency_ms: float | None = None
    token_usage: TokenUsage | None = None
    prompt_length: int | None = None
    # Phase 5A — presentation plan only (no answer mutation).
    response_layout: dict[str, Any] | None = None
