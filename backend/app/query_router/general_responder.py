"""GENERAL_QUERY answers via the configured LLM provider (no retrieval)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.logging import get_logger, log_with_fields
from app.db.models.message import Message
from app.llm.types import BuiltPrompt, LLMGenerationRequest
from app.services.context_builder import ContextBuilder

if TYPE_CHECKING:
    from app.llm.base import LLMProvider

logger = get_logger(__name__)

# Keep general follow-up context small and configurable (token/cost control).
GENERAL_HISTORY_MAX_MESSAGES = 4
GENERAL_HISTORY_MAX_CHARS = 2_000

GENERAL_SYSTEM_PROMPT = """You are Knowra.

You help with general questions that are not answered from private organisational
documents: explanations, writing help, definitions, and similar requests.

You may answer:
- greetings and normal conversation
- general knowledge and definitions
- writing help (agendas, emails, outlines)

Rules:
- Be concise, clear, and professional by default.
- Do NOT invent organization-specific policies, internal figures, employee data, or claim that an answer came from company documents.
- Do NOT fabricate citations or source filenames.
- If the user is clearly asking about their organization's documents or policies, briefly say that needs the document knowledge path — but for this turn you are answering a general question, so stay general.
- Prefer practical, helpful answers without unnecessary preamble.
- Do not claim access to the user's private documents or organisation data.
- Keep safety: refuse harmful criminal activity requests respectfully.
"""

LLM_UNAVAILABLE_GENERAL = (
    "I can help with general questions when a language model is configured. "
    "The general-answer provider isn't available right now. "
    "You can still ask about documents available to you, or ask how this product works."
)


def select_general_history_messages(
    messages: list[Message],
    *,
    max_messages: int = GENERAL_HISTORY_MAX_MESSAGES,
    max_chars: int = GENERAL_HISTORY_MAX_CHARS,
) -> list[Message]:
    """Return a small recent slice of history suitable for general LLM prompts."""
    if not messages or max_messages <= 0 or max_chars <= 0:
        return []

    window = list(messages[-max_messages:])
    while window and len(ContextBuilder.format_history(window) or "") > max_chars:
        window.pop(0)
    return window


def format_general_conversation_history(
    messages: list[Message],
    *,
    max_messages: int = GENERAL_HISTORY_MAX_MESSAGES,
    max_chars: int = GENERAL_HISTORY_MAX_CHARS,
) -> str | None:
    """Format a bounded recent history string for ``GeneralQueryResponder``."""
    selected = select_general_history_messages(
        messages,
        max_messages=max_messages,
        max_chars=max_chars,
    )
    return ContextBuilder.format_history(selected)


class GeneralQueryResponder:
    """Generate uncitable general answers using the shared LLM provider."""

    def __init__(self, llm_provider: "LLMProvider | None" = None) -> None:
        self._llm_provider = llm_provider

    def generate(
        self,
        question: str,
        *,
        conversation_history: str | None = None,
    ) -> str:
        """Return a general answer, or a safe fallback when no LLM is configured."""
        provider = self._llm_provider
        if provider is None:
            return LLM_UNAVAILABLE_GENERAL

        history_block = ""
        if conversation_history and conversation_history.strip():
            # Bound again in case callers pass a larger string.
            history_text = conversation_history.strip()
            if len(history_text) > GENERAL_HISTORY_MAX_CHARS:
                history_text = history_text[-GENERAL_HISTORY_MAX_CHARS:]
            history_block = (
                "Prior conversation (context only — not organizational documents):\n"
                f"{history_text}\n\n"
            )

        user_prompt = (
            f"{history_block}"
            f"User question: {question.strip()}\n\n"
            "Respond helpfully as a general assistant. "
            "Do not invent organization-specific facts or citations."
        )
        prompt = BuiltPrompt(
            system=GENERAL_SYSTEM_PROMPT,
            user=user_prompt,
            messages=[
                {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        request = LLMGenerationRequest(
            question=question.strip(),
            retrieved_chunks=[],
            conversation_history=conversation_history,
            prompt=prompt,
        )
        try:
            result = provider.generate_sync(request)
        except Exception as exc:
            log_with_fields(
                logger,
                logging.WARNING,
                "General-query LLM generation failed",
                reason=type(exc).__name__,
            )
            return LLM_UNAVAILABLE_GENERAL

        answer = (result.answer or "").strip()
        return answer or LLM_UNAVAILABLE_GENERAL
