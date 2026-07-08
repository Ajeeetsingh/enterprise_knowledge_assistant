"""Groq LLM provider implementation."""

from __future__ import annotations

import time

import httpx

from app.llm.base import LLMProvider
from app.llm.exceptions import LLMGenerationError, LLMProviderNotConfiguredError
from app.llm.types import LLMGenerationRequest, LLMGenerationResult, TokenUsage

_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(LLMProvider):
    """Generate answers via the Groq Chat Completions API."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: float,
    ) -> None:
        if not api_key or not api_key.strip():
            raise LLMProviderNotConfiguredError(
                "Groq provider requires GROQ_API_KEY to be set."
            )
        self._api_key = api_key.strip()
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        payload = {
            "model": self._model,
            "messages": request.prompt.messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(
                    _GROQ_CHAT_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            raise LLMGenerationError(
                f"Groq API returned HTTP {exc.response.status_code}: {detail}"
            ) from exc
        except httpx.RequestError as exc:
            raise LLMGenerationError(f"Groq API request failed: {exc}") from exc

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        answer = _extract_answer_text(data)
        token_usage = _extract_token_usage(data)

        return LLMGenerationResult(
            answer=answer,
            provider_name=self.provider_name,
            model=self._model,
            latency_ms=latency_ms,
            token_usage=token_usage,
            raw_metadata={"response_id": data.get("id")},
        )


def _extract_answer_text(data: dict) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMGenerationError("Groq response missing message content.") from exc

    answer = str(content).strip()
    if not answer:
        raise LLMGenerationError("Groq returned an empty answer.")
    return answer


def _extract_token_usage(data: dict) -> TokenUsage | None:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    return TokenUsage(
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
    )
