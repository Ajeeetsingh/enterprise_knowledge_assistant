"""Conversation-aware chat orchestration (Phase 6.6).

Coordinates conversation persistence, context assembly, query routing, and
the existing RAG service without modifying retrieval, ranking, or
authorization logic.

Flow:
    1. Persist the user message.
    2. Build conversation context via ``ContextBuilder``.
    3. Classify via ``QueryRouter`` (with minimal prior-turn route hints):
         - UNSAFE → concise boundary message (no RAG / no general LLM)
         - PRODUCT_HELP → curated answer (no RAG / no LLM)
         - DOCUMENT_QUERY + zero accessible docs → curated message (no RAG)
         - GENERAL_QUERY → configured LLM (no RAG / no citations)
         - DOCUMENT_QUERY → ``RagService.answer_question``
    4. Persist the assistant message on success.
    5. Generate and persist a conversation title on the first message.

If RAG fails after step 1, the user message remains stored and the error
propagates through existing global exception handling. Title generation
never propagates errors.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from app.auth.dependencies import user_has_permission
from app.auth.permissions import Permission
from app.core.logging import get_logger, log_with_fields
from app.db.models.message import Message
from app.db.models.user import User
from app.rag.answer_generator import UNAVAILABLE_MESSAGE
from app.rag.types import Citation, QueryResponse
from app.query_router import QueryRouter, QueryRoute, UserQueryContext, get_query_router
from app.query_router.conversation_hints import infer_route_hints
from app.query_router.document_catalog import build_document_route_catalog
from app.query_router.general_responder import (
    GeneralQueryResponder,
    format_general_conversation_history,
)
from app.query_router.routing_debug import log_final_response_type
from app.query_router.messages import (
    ANSWER_KIND_DOCUMENT_GROUNDED,
    ANSWER_KIND_DOCUMENT_INSUFFICIENT,
    ANSWER_KIND_GENERAL,
    ANSWER_KIND_PRODUCT_HELP,
    ANSWER_KIND_UNSAFE,
    INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE,
)
from app.services.context_builder import (
    DEFAULT_CONTEXT_WINDOW,
    MAX_CONTEXT_CHARACTERS,
    ContextBuilder,
    ConversationContext,
)
from app.services.conversation_service import ConversationService
from app.services.title_generation import generate_conversation_title

if TYPE_CHECKING:
    from app.llm.base import LLMProvider
    from app.services.rag_service import RagService

logger = get_logger(__name__)


@dataclass(frozen=True)
class ConversationChatResult:
    """Outcome of a successful conversation-aware chat turn.

    Attributes:
        conversation_id: The conversation the turn belongs to.
        answer: Generated answer text.
        citations: Serialized citation objects for API persistence.
        confidence_score: Overall answer confidence.
        message: Status message.
        answer_kind: Internal route metadata (not shown in the chat UI).
    """

    conversation_id: uuid.UUID
    answer: str
    citations: list[dict[str, Any]]
    confidence_score: float
    message: str
    answer_kind: str | None = None


class ConversationChatService:
    """Orchestrates conversation memory with query routing and RAG.

    This service owns the conversation / router / RAG integration boundary.
    It does not implement retrieval, document authorization, or vector search
    — those remain in ``RagService`` and the route-layer authorization helpers.
    """

    def __init__(
        self,
        conversation_service: ConversationService,
        *,
        title_llm_provider: "LLMProvider | None" = None,
        query_router: QueryRouter | None = None,
        general_responder: GeneralQueryResponder | None = None,
        llm_provider: "LLMProvider | None | object" = None,
    ) -> None:
        self._conversation_service = conversation_service
        self._title_llm_provider = title_llm_provider
        self._query_router = query_router
        self._general_responder = general_responder
        # None = lazy; False = disabled; provider = use directly.
        self._llm_provider = llm_provider

    def _router(self) -> QueryRouter:
        return self._query_router or get_query_router()

    def _resolve_llm(self) -> "LLMProvider | None":
        if self._llm_provider is False:
            return None
        if self._llm_provider is not None:
            return self._llm_provider  # type: ignore[return-value]
        try:
            from app.config import get_settings
            from app.llm.factory import create_llm_provider

            self._llm_provider = create_llm_provider(get_settings()) or False
        except Exception:
            self._llm_provider = False
        return None if self._llm_provider is False else self._llm_provider  # type: ignore[return-value]

    def _responder(self) -> GeneralQueryResponder:
        if self._general_responder is not None:
            return self._general_responder
        return GeneralQueryResponder(llm_provider=self._resolve_llm())

    def ask_question(
        self,
        user: User,
        conversation_id: uuid.UUID,
        question: str,
        role_name: str,
        rag_service: RagService,
        authorized_sources: frozenset[str] | None,
    ) -> ConversationChatResult:
        """Process a conversation turn and return the generated answer."""
        user_message = self._conversation_service.add_user_message(
            user,
            conversation_id,
            question,
        )

        context = self._build_context_after_user_message(
            user,
            conversation_id,
            question,
            stored_user_message_id=user_message.id,
        )

        sources = authorized_sources if authorized_sources is not None else frozenset()
        route_hints = infer_route_hints(context.history_messages)
        org_aliases = _load_org_aliases()
        route_context = UserQueryContext(
            role_name=role_name,
            can_upload=user_has_permission(user, Permission.DOCUMENT_CREATE),
            has_accessible_documents=len(sources) > 0,
            accessible_document_count=len(sources),
            conversation_hints=route_hints,
            org_aliases=org_aliases,
            document_catalog=build_document_route_catalog(sources),
        )
        decision = self._router().route(context.current_question, route_context)
        # RAG may use a larger conversational window; general answers stay small.
        rag_history = ContextBuilder.format_history(context.history_messages)
        rag_executed = False

        if decision.route == QueryRoute.GENERAL_QUERY:
            general_history = _general_history_for_prompt(
                context.history_messages,
                previous_route=route_hints.previous_route,
            )
            assistant_content = self._responder().generate(
                context.current_question,
                conversation_history=general_history,
            )
            citations: list[dict[str, Any]] = []
            confidence = float(decision.confidence)
            status_message = decision.message or "Answered as a general query."
            answer_kind = decision.answer_kind or ANSWER_KIND_GENERAL
        elif decision.should_skip_rag:
            # UNSAFE / PRODUCT_HELP / DOCUMENT zero-doc curated answers.
            assistant_content = decision.answer or ""
            citations = []
            confidence = float(decision.confidence)
            status_message = decision.message or "Answered without document retrieval."
            answer_kind = decision.answer_kind or (
                ANSWER_KIND_UNSAFE
                if decision.route == QueryRoute.UNSAFE
                else ANSWER_KIND_PRODUCT_HELP
            )
        else:
            # Always pass a frozenset (never None) so RAG cannot become unrestricted.
            rag_executed = True
            query_response = rag_service.answer_question(
                context.current_question,
                role_name,
                sources,
                conversation_history=rag_history,
            )
            assistant_content = resolve_assistant_content(query_response)
            citations = _serialize_citations(query_response.citations)
            confidence = query_response.confidence_score
            status_message = query_response.message
            answer_kind = _document_answer_kind(query_response, assistant_content)

        try:
            log_final_response_type(
                question=context.current_question,
                answer_kind=answer_kind or "unknown",
                rag_executed=rag_executed,
            )
        except Exception:  # noqa: BLE001
            pass

        self._conversation_service.add_assistant_message(
            user,
            conversation_id,
            content=assistant_content,
            citations=citations,
            confidence_score=confidence,
        )

        self._maybe_generate_title(user, conversation_id, question)

        return ConversationChatResult(
            conversation_id=conversation_id,
            answer=assistant_content,
            citations=citations,
            confidence_score=confidence,
            message=status_message,
            answer_kind=answer_kind,
        )

    def _build_context_after_user_message(
        self,
        user: User,
        conversation_id: uuid.UUID,
        question: str,
        *,
        stored_user_message_id: uuid.UUID,
    ) -> ConversationContext:
        """Build context using prior history only."""
        recent = self._conversation_service.get_recent_messages(
            user,
            conversation_id,
            DEFAULT_CONTEXT_WINDOW,
        )
        history = _history_excluding_stored_turn(recent, stored_user_message_id)
        clean_question = question.strip()
        return ContextBuilder.build(
            clean_question,
            history,
            max_chars=MAX_CONTEXT_CHARACTERS,
        )

    def _maybe_generate_title(
        self,
        user: User,
        conversation_id: uuid.UUID,
        question: str,
    ) -> None:
        """Generate and persist a title after the conversation's first message."""
        try:
            conversation = self._conversation_service.get_conversation(user, conversation_id)
            if conversation.title is not None:
                return

            title = generate_conversation_title(question, self._title_llm_provider)
            self._conversation_service.set_auto_generated_title(user, conversation_id, title)
        except Exception as exc:
            log_with_fields(
                logger,
                logging.WARNING,
                "Conversation auto-title generation failed; leaving title unset",
                conversation_id=str(conversation_id),
                reason=type(exc).__name__,
            )


def _load_org_aliases() -> tuple[str, ...]:
    """Load configured tenant aliases for data-driven DOCUMENT routing."""
    try:
        from app.config import get_settings

        settings = get_settings()
        aliases: list[str] = []
        display = (getattr(settings, "org_display_name", None) or "").strip()
        if display:
            aliases.append(display)
        for alias in getattr(settings, "org_aliases", None) or []:
            cleaned = str(alias).strip()
            if cleaned and cleaned not in aliases:
                aliases.append(cleaned)
        return tuple(aliases)
    except Exception:  # noqa: BLE001
        return ()


def _document_answer_kind(query_response: QueryResponse, assistant_content: str) -> str:
    """Map a RAG response to an internal answer_kind label."""
    sources_used = list(getattr(query_response, "sources_used", None) or [])
    citations = list(getattr(query_response, "citations", None) or [])
    if not citations and assistant_content.strip() in {
        INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE,
        "No relevant documents found for this query.",
    }:
        return ANSWER_KIND_DOCUMENT_INSUFFICIENT
    if citations:
        return ANSWER_KIND_DOCUMENT_GROUNDED
    if float(getattr(query_response, "confidence_score", 0.0) or 0.0) <= 0.0 and not sources_used:
        return ANSWER_KIND_DOCUMENT_INSUFFICIENT
    return ANSWER_KIND_DOCUMENT_GROUNDED


def resolve_assistant_content(query_response: QueryResponse) -> str:
    """Return non-blank assistant content suitable for conversation persistence."""
    answer = query_response.answer.strip()
    if answer:
        return answer

    message = query_response.message.strip()
    if message:
        return message

    return UNAVAILABLE_MESSAGE


def _general_history_for_prompt(
    history_messages: list[Message],
    *,
    previous_route: QueryRoute | None,
) -> str | None:
    """Return bounded history for general answers, avoiding document-topic bleed.

    When the previous turn was document-grounded or unsafe, omit history so a
    topic-changing GENERAL question does not pull organizational excerpts into
    the general LLM prompt. Follow-ups within a general/product thread keep a
    small recent window.
    """
    if previous_route in {QueryRoute.DOCUMENT_QUERY, QueryRoute.UNSAFE}:
        return None
    return format_general_conversation_history(history_messages)


def _history_excluding_stored_turn(
    recent_messages: list[Message],
    stored_user_message_id: uuid.UUID,
) -> list[Message]:
    """Drop the just-persisted user message from the history window."""
    return [message for message in recent_messages if message.id != stored_user_message_id]


def _serialize_citations(citations: list[Citation]) -> list[dict[str, Any]]:
    """Convert native RAG citations into JSON-serializable dicts."""
    return [
        {
            "source": citation.source,
            "excerpt": citation.excerpt,
            "confidence": citation.confidence,
            "page": getattr(citation, "page", None),
        }
        for citation in citations
    ]


def build_conversation_chat_service(db: Session) -> ConversationChatService:
    """Construct a ``ConversationChatService`` bound to *db*."""
    from app.services.conversation_service import build_conversation_service
    from app.services.title_generation import get_title_llm_provider

    return ConversationChatService(
        build_conversation_service(db),
        title_llm_provider=get_title_llm_provider(),
    )
