"""Conversation follow-up hints for context-aware query routing."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.db.models.message import Message, MessageRole
from app.query_router.messages import (
    ANSWER_KIND_DOCUMENT_GROUNDED,
    ANSWER_KIND_DOCUMENT_INSUFFICIENT,
    ANSWER_KIND_DOCUMENT_UNAVAILABLE,
    ANSWER_KIND_GENERAL,
    ANSWER_KIND_PRODUCT_HELP,
    ANSWER_KIND_UNSAFE,
    INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE,
    ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE,
)
from app.query_router.safety import UNSAFE_BOUNDARY_MESSAGE
from app.query_router.types import QueryRoute

# Compact follow-up cues — not a full NLU grammar.
_FOLLOW_UP = re.compile(
    r"^\s*("
    r"what about\b|how about\b|and (?:for|about|the)\b|"
    r"can you (?:give|provide|show|share|explain) (?:me )?(?:an? |more |another )?"
    r"(?:example|detail|details|that)|"
    r"(?:give|provide) (?:me )?(?:an? )?example\b|"
    r"more details?\b|tell me more\b|continue\b|go on\b|"
    r"same (?:for|with)\b|similarly\b|also\b|"
    r"does (?:it|that|this)\b|can it\b|is it\b|"
    r"what if\b|and contractors\b|and adoptive\b|"
    r"summarize\s+that\b|summarise\s+that\b|"
    r"make\s+it\s+(?:simpler|simpler\s+please|shorter|clearer|easier)\b|"
    r"in\s+(?:simpler|simpler\s+terms|plain\s+english)\b|"
    r"explain\s+(?:that|this|it)\b"
    r")",
    re.I,
)

# Max prior turns considered when building routing hints (user+assistant pairs).
ROUTING_HINT_MAX_TURNS = 3


@dataclass(frozen=True)
class ConversationRouteHints:
    """Minimal prior-turn hints for follow-up routing (not authorization)."""

    previous_user_query: str | None = None
    previous_route: QueryRoute | None = None
    previous_answer_kind: str | None = None


def looks_like_follow_up(query: str) -> bool:
    """Return whether *query* looks like a conversational continuation."""
    return bool(_FOLLOW_UP.search(query.strip()))


def infer_route_hints(history_messages: list[Message]) -> ConversationRouteHints:
    """Infer previous route/answer kind from recent messages (no extra LLM).

    Uses the last completed user→assistant pair only. Citations imply a
    document-grounded turn; known curated messages map to document/product;
    otherwise the previous turn is treated as general.
    """
    if not history_messages:
        return ConversationRouteHints()

    # history is oldest→newest and excludes the just-persisted current user turn.
    prev_assistant: Message | None = None
    prev_user: Message | None = None
    for message in reversed(history_messages):
        if prev_assistant is None and message.role == MessageRole.ASSISTANT.value:
            prev_assistant = message
            continue
        if (
            prev_assistant is not None
            and prev_user is None
            and message.role == MessageRole.USER.value
        ):
            prev_user = message
            break

    if prev_assistant is None:
        return ConversationRouteHints(
            previous_user_query=prev_user.content if prev_user else None,
        )

    route, kind = _infer_assistant_route(prev_assistant)
    return ConversationRouteHints(
        previous_user_query=prev_user.content.strip() if prev_user else None,
        previous_route=route,
        previous_answer_kind=kind,
    )


def _infer_assistant_route(assistant: Message) -> tuple[QueryRoute, str]:
    citations = assistant.citations or []
    content = (assistant.content or "").strip()

    if citations:
        return QueryRoute.DOCUMENT_QUERY, ANSWER_KIND_DOCUMENT_GROUNDED

    if content == ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE:
        return QueryRoute.DOCUMENT_QUERY, ANSWER_KIND_DOCUMENT_UNAVAILABLE

    if content == INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE or content.startswith(
        "I couldn't find enough relevant information in the documents"
    ):
        return QueryRoute.DOCUMENT_QUERY, ANSWER_KIND_DOCUMENT_INSUFFICIENT

    if (
        content.startswith("I'm Knowra")
        or content.startswith("I'm the Enterprise Knowledge Assistant")
        or (
            ("Knowra" in content or "Enterprise Knowledge Assistant" in content)
            and "citations" in content.lower()
        )
    ):
        return QueryRoute.PRODUCT_HELP, ANSWER_KIND_PRODUCT_HELP

    if content == UNSAFE_BOUNDARY_MESSAGE or content.startswith(
        "I can't help with that request"
    ):
        return QueryRoute.UNSAFE, ANSWER_KIND_UNSAFE

    # No citations and not a known curated document/product/safety message.
    return QueryRoute.GENERAL_QUERY, ANSWER_KIND_GENERAL
