"""LLM layer exceptions."""


class LLMError(Exception):
    """Base error for LLM generation failures."""


class LLMProviderNotConfiguredError(LLMError):
    """Raised when a provider is selected but not fully configured."""


class LLMProviderNotImplementedError(LLMError):
    """Raised when a provider placeholder is invoked."""


class LLMGenerationError(LLMError):
    """Raised when an LLM API call fails."""
