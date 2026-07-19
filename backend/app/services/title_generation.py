"""Conversation title generation.

Generates a short, human-readable conversation title from a user's first
message. The LLM path is tried first when a provider is configured; any
failure at all (provider unavailable, network/API error, empty or malformed
response) falls back to a fully deterministic, keyword-extraction title.

`generate_conversation_title` is designed to never raise — a conversation
must always end up with *some* reasonable title, and title generation must
never be able to break an otherwise-successful chat turn.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from app.config import get_settings
from app.core.logging import get_logger, log_with_fields
from app.llm.base import LLMProvider
from app.llm.exceptions import LLMError
from app.llm.factory import create_llm_provider
from app.llm.types import BuiltPrompt, LLMGenerationRequest

logger = get_logger(__name__)

MAX_TITLE_WORDS = 6
FALLBACK_TITLE = "New Conversation"

# Title generation must never noticeably slow down a chat response. This is
# deliberately much shorter than `llm_timeout_seconds` (used for the main
# answer) so a slow/unreachable provider fails fast and falls back to the
# deterministic title instead of stalling the whole chat turn.
DEFAULT_TITLE_TIMEOUT_SECONDS = 8.0

_TITLE_SYSTEM_PROMPT = (
    "You generate short titles for conversations in an enterprise knowledge "
    "assistant. Given the user's first question, respond with ONLY a "
    "concise title of 4-6 words that captures the topic.\n"
    "Rules:\n"
    "- Use Title Case.\n"
    "- Preserve acronyms and proper nouns exactly as written (e.g. FY2026, KYC, GDPR).\n"
    '- Do not use quotes, a trailing period, or any explanation — respond with the title text alone.\n'
    "\n"
    "Examples:\n"
    'Question: "What are the main types of commercial paper issuers?"\n'
    "Title: Commercial Paper Issuers\n\n"
    'Question: "Explain Project Phoenix."\n'
    "Title: Project Phoenix\n\n"
    'Question: "Summarize FY2026 strategic priorities."\n'
    "Title: FY2026 Strategic Priorities\n\n"
    'Question: "How do Money Market Funds participate in the repo market?"\n'
    "Title: Money Market Funds & Repo Market"
)

_WORD_RE = re.compile(r"[A-Za-z0-9&']+")

# Generic function/question words that carry no topical meaning of their own.
# Deliberately domain-agnostic (no document- or example-specific terms) so
# the fallback generalizes to any future question, not just the examples
# above — those are handled well by the LLM path's few-shot prompt.
_TITLE_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "by", "can", "could",
        "describe", "did", "do", "does", "explain", "for", "from", "give", "has",
        "have", "how", "i", "in", "is", "it", "its", "kind", "kinds", "let",
        "list", "main", "me", "of", "on", "our", "outline", "please", "provide",
        "say", "should", "show", "so", "summarise", "summarize", "tell", "that",
        "the", "their", "there", "these", "this", "those", "to", "type", "types",
        "was", "we", "were", "what", "when", "where", "which", "who", "whom",
        "why", "will", "with", "would", "you", "your",
    }
)


def generate_conversation_title(
    question: str,
    llm_provider: LLMProvider | None,
) -> str:
    """Return a short (<=6 word) conversation title derived from *question*.

    Tries *llm_provider* first when available; falls back to a fully
    deterministic keyword-extraction title on any failure. Always returns a
    non-empty string — this function never raises.

    Args:
        question: The user's first message in the conversation.
        llm_provider: Configured LLM provider, or ``None`` to always use the
            deterministic fallback (e.g. when no provider is configured).

    Returns:
        A short, Title Case conversation title.
    """
    clean_question = question.strip()
    if not clean_question:
        return FALLBACK_TITLE

    if llm_provider is not None:
        llm_title = _try_llm_title(clean_question, llm_provider)
        if llm_title:
            return llm_title

    return _deterministic_title(clean_question)


def _try_llm_title(question: str, llm_provider: LLMProvider) -> str | None:
    """Attempt LLM-based title generation. Returns ``None`` on any failure."""
    user_message = f'Question: "{question}"\nTitle:'
    prompt = BuiltPrompt(
        system=_TITLE_SYSTEM_PROMPT,
        user=user_message,
        messages=[
            {"role": "system", "content": _TITLE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    request = LLMGenerationRequest(
        question=question,
        retrieved_chunks=[],
        conversation_history=None,
        prompt=prompt,
    )

    try:
        result = llm_provider.generate_sync(request)
    except LLMError as exc:
        log_with_fields(
            logger,
            logging.WARNING,
            "Title generation LLM call failed; using deterministic fallback",
            reason=type(exc).__name__,
        )
        return None
    except Exception as exc:  # defensive: title generation must never raise
        log_with_fields(
            logger,
            logging.WARNING,
            "Title generation LLM call raised an unexpected error; using deterministic fallback",
            reason=type(exc).__name__,
        )
        return None

    return _clean_llm_title(result.answer)


def _clean_llm_title(raw: str) -> str | None:
    """Normalize a raw LLM response into a usable title, or ``None``."""
    if not raw or not raw.strip():
        return None

    title = raw.strip().splitlines()[0].strip()
    if title.lower().startswith("title:"):
        title = title[len("title:") :].strip()
    title = title.strip(" \"'.")

    if not title:
        return None

    words = title.split()
    if len(words) > MAX_TITLE_WORDS:
        title = " ".join(words[:MAX_TITLE_WORDS])
    return title


def _deterministic_title(question: str) -> str:
    """Extract important terms, strip stopwords, and Title Case them."""
    tokens = _WORD_RE.findall(question)
    important = [token for token in tokens if token.lower() not in _TITLE_STOPWORDS]

    selected = important if important else tokens
    selected = selected[:MAX_TITLE_WORDS]

    if not selected:
        return FALLBACK_TITLE

    return " ".join(_title_case_word(token) for token in selected)


def _title_case_word(word: str) -> str:
    """Title-case *word*, preserving existing internal capitalization/digits.

    Acronyms and mixed-case tokens like "FY2026" or "KYC" must not be
    lowercased into "Fy2026"/"Kyc" — only plain, all-lowercase-after-first-
    letter words are re-capitalized.
    """
    if any(char.isdigit() for char in word) or any(char.isupper() for char in word[1:]):
        return word
    return word[:1].upper() + word[1:].lower()


@lru_cache
def get_title_llm_provider() -> LLMProvider | None:
    """Return a cached LLM provider for title generation, or ``None``.

    Reuses the configured provider/model but overrides the timeout to a
    much shorter value than the main answer-generation timeout (see
    `DEFAULT_TITLE_TIMEOUT_SECONDS`). Never raises: any provider
    construction failure (e.g. misconfigured credentials) is logged and
    treated as "no provider available", so title generation always falls
    back to the deterministic path instead of breaking chat requests.
    """
    settings = get_settings()
    title_settings = settings.model_copy(
        update={
            "llm_timeout_seconds": min(
                settings.llm_timeout_seconds, DEFAULT_TITLE_TIMEOUT_SECONDS
            )
        }
    )
    try:
        return create_llm_provider(title_settings)
    except Exception as exc:  # defensive: never break request wiring
        log_with_fields(
            logger,
            logging.WARNING,
            "Title generation LLM provider could not be constructed; "
            "deterministic fallback will be used",
            reason=type(exc).__name__,
        )
        return None
