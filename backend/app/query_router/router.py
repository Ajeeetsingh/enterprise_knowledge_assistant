"""Top-level query router sitting above the secure document RAG pipeline."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

from app.core.logging import get_logger, log_with_fields
from app.query_router.conversation_hints import looks_like_follow_up
from app.query_router.knowledge_classifier import KnowledgeRouteClassifier, KnowledgeRouteResult
from app.query_router.knowledge_signals import score_document_signals, score_general_signals
from app.query_router.messages import (
    ANSWER_KIND_DOCUMENT_GROUNDED,
    ANSWER_KIND_DOCUMENT_UNAVAILABLE,
    ANSWER_KIND_GENERAL,
    ANSWER_KIND_PRODUCT_HELP,
    ANSWER_KIND_UNSAFE,
    ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE,
)
from app.query_router.product_matcher import (
    DEFAULT_SEMANTIC_THRESHOLD,
    ProductIntentMatcher,
)
from app.query_router.safety import UNSAFE_BOUNDARY_MESSAGE, assess_unsafe_intent
from app.query_router.types import QueryRoute, RouteDecision, UserQueryContext

if TYPE_CHECKING:
    from app.llm.base import LLMProvider

logger = get_logger(__name__)

_STRONG = 0.75

# Classifications weak enough that prior-turn inheritance may apply.
_WEAK_METHODS = frozenset(
    {
        "default_document_safe",
        "deterministic_document_mild",
        "deterministic_general_mild",
        "llm_classifier",
    }
)

_INHERITABLE_ROUTES = frozenset(
    {
        QueryRoute.DOCUMENT_QUERY,
        QueryRoute.GENERAL_QUERY,
        QueryRoute.PRODUCT_HELP,
    }
)


class QueryRouter:
    """Classify questions into product-help, document RAG, general, or unsafe paths.

    Routing priority:
    1. High-confidence UNSAFE short-circuit (never blocks legitimate policy Qs)
    2. PRODUCT_HELP curated catalogue match
    3. Current-turn DOCUMENT vs GENERAL classification
    4. Ambiguous follow-up inheritance from the prior turn
    5. DOCUMENT zero-doc short-circuit or RAG
    """

    def __init__(
        self,
        product_matcher: ProductIntentMatcher | None = None,
        *,
        knowledge_classifier: KnowledgeRouteClassifier | None = None,
        llm_provider: "LLMProvider | None | object" = None,
        semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    ) -> None:
        self._product_matcher = product_matcher or ProductIntentMatcher(
            semantic_threshold=semantic_threshold,
        )
        self._llm_provider = llm_provider
        self._knowledge_classifier = knowledge_classifier

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

    def _classifier(self) -> KnowledgeRouteClassifier:
        if self._knowledge_classifier is not None:
            return self._knowledge_classifier
        return KnowledgeRouteClassifier(llm_provider=self._resolve_llm())

    def route(self, query: str, context: UserQueryContext) -> RouteDecision:
        """Classify *query* and return a route decision (optionally with answer)."""
        # 1) Lightweight safety — high-confidence harmful intent only.
        safety = assess_unsafe_intent(query)
        if safety.is_unsafe:
            log_with_fields(
                logger,
                logging.INFO,
                "Query routed to UNSAFE",
                method=safety.method,
                confidence=safety.confidence,
            )
            return RouteDecision(
                route=QueryRoute.UNSAFE,
                confidence=safety.confidence,
                answer=UNSAFE_BOUNDARY_MESSAGE,
                message="Request declined by safety boundary.",
                answer_kind=ANSWER_KIND_UNSAFE,
                classification_method=safety.method,
            )

        # 2) Product-help curated catalogue.
        product = self._product_matcher.match_and_answer(query, context)
        if product is not None:
            matched, answer = product
            log_with_fields(
                logger,
                logging.INFO,
                "Query routed to PRODUCT_HELP",
                intent_id=matched.intent.id,
                match_type=matched.match_type,
                confidence=matched.confidence,
                role=context.role_name,
                has_documents=context.has_accessible_documents,
                can_upload=context.can_upload,
            )
            return RouteDecision(
                route=QueryRoute.PRODUCT_HELP,
                confidence=matched.confidence,
                intent_id=matched.intent.id,
                answer=answer,
                message="Answered from curated product knowledge.",
                answer_kind=ANSWER_KIND_PRODUCT_HELP,
                classification_method=matched.match_type,
            )

        # 3) Current-turn DOCUMENT vs GENERAL (data-driven + semantic signals).
        signal_context = context.to_signal_context()
        knowledge = self._classifier().classify(query, signal_context)

        # 4) Ambiguous follow-ups may inherit the previous route; strong
        #    current-turn signals always override inheritance.
        knowledge = self._maybe_apply_follow_up_context(query, knowledge, context)

        log_with_fields(
            logger,
            logging.INFO,
            "Query knowledge route classified",
            route=knowledge.route.value,
            confidence=knowledge.confidence,
            method=knowledge.method,
            signals=list(knowledge.signals),
            document_score=knowledge.document_score,
            general_score=knowledge.general_score,
            has_documents=context.has_accessible_documents,
            catalog_titles=len(context.document_catalog.titles),
            org_alias_count=len(context.org_aliases),
        )

        try:
            from app.query_router.routing_debug import log_routing_stage

            log_routing_stage(
                question=query,
                route=knowledge.route.value,
                method=knowledge.method,
                confidence=knowledge.confidence,
                document_score=knowledge.document_score,
                general_score=knowledge.general_score,
                signals=knowledge.signals,
                rag_selected=knowledge.route == QueryRoute.DOCUMENT_QUERY
                and context.has_accessible_documents,
            )
        except Exception:  # noqa: BLE001 — debug logging must never break routing
            pass

        if knowledge.route == QueryRoute.GENERAL_QUERY:
            return RouteDecision(
                route=QueryRoute.GENERAL_QUERY,
                confidence=knowledge.confidence,
                message="Routed to general assistant response.",
                answer_kind=ANSWER_KIND_GENERAL,
                classification_method=knowledge.method,
            )

        if knowledge.route == QueryRoute.PRODUCT_HELP:
            # Inherited product follow-up without a fresh catalogue hit.
            # Fall through to general rather than inventing product copy or RAG.
            return RouteDecision(
                route=QueryRoute.GENERAL_QUERY,
                confidence=knowledge.confidence,
                message="Product follow-up without catalogue match; using general assistant.",
                answer_kind=ANSWER_KIND_GENERAL,
                classification_method=knowledge.method,
            )

        # DOCUMENT_QUERY — short-circuit when the user has nothing to search.
        if not context.has_accessible_documents:
            return RouteDecision(
                route=QueryRoute.DOCUMENT_QUERY,
                confidence=knowledge.confidence,
                answer=ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE,
                message="No accessible documents available for retrieval.",
                answer_kind=ANSWER_KIND_DOCUMENT_UNAVAILABLE,
                classification_method=knowledge.method,
            )

        return RouteDecision(
            route=QueryRoute.DOCUMENT_QUERY,
            confidence=knowledge.confidence,
            message="Routed to document knowledge retrieval.",
            answer_kind=ANSWER_KIND_DOCUMENT_GROUNDED,
            classification_method=knowledge.method,
        )

    def _maybe_apply_follow_up_context(
        self,
        query: str,
        knowledge: KnowledgeRouteResult,
        context: UserQueryContext,
    ) -> KnowledgeRouteResult:
        hints = context.conversation_hints
        if hints is None or hints.previous_route is None:
            return knowledge
        if hints.previous_route not in _INHERITABLE_ROUTES:
            return knowledge
        if not looks_like_follow_up(query):
            return knowledge
        # Explicit current-turn DOCUMENT/GENERAL signals always win.
        if _has_strong_current_override(query, context):
            return knowledge
        if knowledge.method in {"deterministic_document", "deterministic_general"}:
            return knowledge
        if knowledge.method not in _WEAK_METHODS and knowledge.confidence >= _STRONG:
            return knowledge

        return KnowledgeRouteResult(
            route=hints.previous_route,
            confidence=max(0.7, min(knowledge.confidence + 0.15, 0.85)),
            method="context_follow_up",
            signals=("follow_up", f"prev:{hints.previous_route.value}") + knowledge.signals,
        )


def _has_strong_current_override(
    query: str,
    context: UserQueryContext | None = None,
) -> bool:
    """True when the current turn has strong DOCUMENT or GENERAL signals."""
    signal_context = context.to_signal_context() if context is not None else None
    doc = score_document_signals(query, signal_context)
    gen = score_general_signals(query, signal_context)
    return doc.score >= _STRONG or gen.score >= _STRONG


@lru_cache
def get_query_router() -> QueryRouter:
    """Return the process-wide query router singleton."""
    return QueryRouter()
