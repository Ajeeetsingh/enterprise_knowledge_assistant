"""LLM generation layer for retrieval-augmented answers."""

from app.llm.base import LLMProvider
from app.llm.exceptions import LLMError, LLMGenerationError, LLMProviderNotConfiguredError
from app.llm.factory import create_llm_provider
from app.llm.prompt_builder import PromptBuilder
from app.llm.types import (
    BuiltPrompt,
    GenerationOutcome,
    LLMGenerationRequest,
    LLMGenerationResult,
    TokenUsage,
)

__all__ = [
    "BuiltPrompt",
    "GenerationOutcome",
    "LLMGenerationRequest",
    "LLMGenerationResult",
    "LLMProvider",
    "LLMError",
    "LLMGenerationError",
    "LLMProviderNotConfiguredError",
    "PromptBuilder",
    "TokenUsage",
    "create_llm_provider",
]
