"""Public guest/demo query orchestration (no persistence, no RAG)."""

from __future__ import annotations

from dataclasses import dataclass

from app.query_router.conversation_hints import ConversationRouteHints
from app.query_router.general_responder import (
    GENERAL_HISTORY_MAX_CHARS,
    GeneralQueryResponder,
    format_general_conversation_history,
)
from app.query_router.messages import (
    ANSWER_KIND_GENERAL,
    ANSWER_KIND_GUEST_AUTH_REQUIRED,
    ANSWER_KIND_PRODUCT_HELP,
    ANSWER_KIND_UNSAFE,
    GUEST_DOCUMENT_AUTH_REQUIRED_MESSAGE,
)
from app.query_router.router import QueryRouter, get_query_router
from app.query_router.types import QueryRoute, UserQueryContext
from app.schemas.demo import GuestAskRequest, GuestAskResponse, GuestHistoryMessage


@dataclass(frozen=True)
class _GuestTurn:
    role: str
    content: str
    answer_kind: str | None = None


# Lightweight stand-in for ORM Message when formatting general history.
class _HistoryAdapter:
    __slots__ = ("role", "content")

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content


def build_guest_query_context(
    history: list[GuestHistoryMessage],
) -> UserQueryContext:
    """Build an honest guest context — zero documents, no upload, no fake roles."""
    return UserQueryContext(
        role_name="Guest",
        can_upload=False,
        has_accessible_documents=False,
        accessible_document_count=0,
        conversation_hints=_hints_from_guest_history(history),
        is_guest=True,
    )


def _hints_from_guest_history(
    history: list[GuestHistoryMessage],
) -> ConversationRouteHints:
    if not history:
        return ConversationRouteHints()

    prev_assistant: GuestHistoryMessage | None = None
    prev_user: GuestHistoryMessage | None = None
    for item in reversed(history):
        if prev_assistant is None and item.role == "assistant":
            prev_assistant = item
            continue
        if (
            prev_assistant is not None
            and prev_user is None
            and item.role == "user"
        ):
            prev_user = item
            break

    if prev_assistant is None:
        return ConversationRouteHints(
            previous_user_query=prev_user.content if prev_user else None,
        )

    route, kind = _route_from_answer_kind(prev_assistant.answer_kind)
    return ConversationRouteHints(
        previous_user_query=prev_user.content if prev_user else None,
        previous_route=route,
        previous_answer_kind=kind,
    )


def _route_from_answer_kind(
    answer_kind: str | None,
) -> tuple[QueryRoute | None, str | None]:
    if not answer_kind:
        return None, None
    mapping: dict[str, QueryRoute] = {
        ANSWER_KIND_PRODUCT_HELP: QueryRoute.PRODUCT_HELP,
        ANSWER_KIND_GENERAL: QueryRoute.GENERAL_QUERY,
        ANSWER_KIND_UNSAFE: QueryRoute.UNSAFE,
        ANSWER_KIND_GUEST_AUTH_REQUIRED: QueryRoute.DOCUMENT_QUERY,
        "document_unavailable": QueryRoute.DOCUMENT_QUERY,
        "document_grounded": QueryRoute.DOCUMENT_QUERY,
        "document_insufficient": QueryRoute.DOCUMENT_QUERY,
    }
    route = mapping.get(answer_kind)
    return route, answer_kind if route else None


class GuestDemoService:
    """Answer guest demo questions without RAG, persistence, or document ACL."""

    def __init__(
        self,
        *,
        query_router: QueryRouter | None = None,
        general_responder: GeneralQueryResponder | None = None,
    ) -> None:
        self._query_router = query_router
        self._general_responder = general_responder

    def _router(self) -> QueryRouter:
        return self._query_router or get_query_router()

    def _responder(self) -> GeneralQueryResponder:
        if self._general_responder is not None:
            return self._general_responder
        try:
            from app.config import get_settings
            from app.llm.factory import create_llm_provider

            provider = create_llm_provider(get_settings())
        except Exception:
            provider = None
        return GeneralQueryResponder(llm_provider=provider)

    def ask(self, request: GuestAskRequest) -> GuestAskResponse:
        """Route and answer a guest question. Never invokes RAG or persistence."""
        context = build_guest_query_context(request.history)
        decision = self._router().route(request.question, context)

        # DOCUMENT must never retrieve — return a sign-in CTA response.
        if decision.route == QueryRoute.DOCUMENT_QUERY:
            return GuestAskResponse(
                answer=GUEST_DOCUMENT_AUTH_REQUIRED_MESSAGE,
                confidence_score=float(decision.confidence),
                message="Document answers require authentication.",
                answer_kind=ANSWER_KIND_GUEST_AUTH_REQUIRED,
                requires_auth=True,
            )

        if decision.route == QueryRoute.GENERAL_QUERY:
            history_text = _format_guest_general_history(request.history)
            answer = self._responder().generate(
                request.question,
                conversation_history=history_text,
            )
            return GuestAskResponse(
                answer=answer,
                confidence_score=float(decision.confidence),
                message=decision.message or "Answered as a general query.",
                answer_kind=ANSWER_KIND_GENERAL,
                requires_auth=False,
            )

        # PRODUCT_HELP / UNSAFE curated answers (and any other skip-RAG path).
        answer = (decision.answer or "").strip()
        if not answer:
            # Should not happen for product/unsafe; fail closed without RAG.
            answer = (
                "I can help with product questions and general knowledge in this demo. "
                "Sign in to ask about your organisation's documents."
            )
            return GuestAskResponse(
                answer=answer,
                confidence_score=float(decision.confidence),
                message="Guest demo could not produce a curated answer.",
                answer_kind=ANSWER_KIND_GUEST_AUTH_REQUIRED,
                requires_auth=True,
            )

        return GuestAskResponse(
            answer=answer,
            confidence_score=float(decision.confidence),
            message=decision.message or "Answered without document retrieval.",
            answer_kind=decision.answer_kind,
            requires_auth=False,
        )


def _format_guest_general_history(history: list[GuestHistoryMessage]) -> str | None:
    if not history:
        return None
    # Prefer recent general/product turns; skip very long document-auth prompts.
    adapters = [
        _HistoryAdapter(item.role, item.content[:GENERAL_HISTORY_MAX_CHARS])
        for item in history
        if item.answer_kind != ANSWER_KIND_GUEST_AUTH_REQUIRED
    ]
    if not adapters:
        adapters = [
            _HistoryAdapter(item.role, item.content[:GENERAL_HISTORY_MAX_CHARS])
            for item in history
        ]
    return format_general_conversation_history(adapters)  # type: ignore[arg-type]
