"""Classify DOCUMENT_QUERY vs GENERAL_QUERY after product-help miss."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.logging import get_logger, log_with_fields
from app.llm.types import BuiltPrompt, LLMGenerationRequest
from app.query_router.knowledge_signals import score_document_signals, score_general_signals
from app.query_router.route_signals import RouteSignalContext
from app.query_router.types import QueryRoute

if TYPE_CHECKING:
    from app.llm.base import LLMProvider

logger = get_logger(__name__)

_HIGH = 0.75
_MILD = 0.55

_CLASSIFIER_SYSTEM = """You classify user messages for Knowra, an internal knowledge Q&A product.
Reply with exactly one label and nothing else:
DOCUMENT_QUERY
or
GENERAL_QUERY

DOCUMENT_QUERY — needs this organization's documents, policies, internal reports, or company-specific facts.
GENERAL_QUERY — greetings, writing help, or general knowledge/definitions not about this organization's documents.

Never invent a third label."""


@dataclass(frozen=True)
class KnowledgeRouteResult:
    """Result of DOCUMENT vs GENERAL classification."""

    route: QueryRoute
    confidence: float
    method: str
    signals: tuple[str, ...] = ()
    document_score: float = 0.0
    general_score: float = 0.0


class KnowledgeRouteClassifier:
    """Layered DOCUMENT vs GENERAL classifier (deterministic first, LLM only if needed)."""

    def __init__(self, llm_provider: "LLMProvider | None" = None) -> None:
        self._llm_provider = llm_provider

    def classify(
        self,
        query: str,
        context: RouteSignalContext | None = None,
    ) -> KnowledgeRouteResult:
        """Classify *query* as DOCUMENT_QUERY or GENERAL_QUERY."""
        signal_context = context or RouteSignalContext()
        # Cheap signals first. Semantic enterprise intent runs only when the
        # deterministic scores are still ambiguous (keeps routing fast).
        cheap_doc = score_document_signals(query, signal_context, allow_semantic=False)
        gen = score_general_signals(query, signal_context)

        if cheap_doc.score >= _HIGH and cheap_doc.score > gen.score:
            return KnowledgeRouteResult(
                QueryRoute.DOCUMENT_QUERY,
                cheap_doc.score,
                "deterministic_document",
                cheap_doc.signals,
                document_score=cheap_doc.score,
                general_score=gen.score,
            )
        # Strong greetings / writing-help / jokes can skip semantic. Definition-like
        # GENERAL scores must still allow semantic enterprise-intent when the user
        # has accessible documents (e.g. "What is <org>'s mission?").
        if gen.score >= _HIGH and gen.score > cheap_doc.score:
            definitional = "definition_without_org" in gen.signals
            if not definitional or not signal_context.has_accessible_documents:
                return KnowledgeRouteResult(
                    QueryRoute.GENERAL_QUERY,
                    gen.score,
                    "deterministic_general",
                    gen.signals,
                    document_score=cheap_doc.score,
                    general_score=gen.score,
                )

        doc = score_document_signals(query, signal_context, allow_semantic=True)

        if doc.score >= _HIGH and doc.score > gen.score:
            return KnowledgeRouteResult(
                QueryRoute.DOCUMENT_QUERY,
                doc.score,
                "deterministic_document",
                doc.signals,
                document_score=doc.score,
                general_score=gen.score,
            )
        if gen.score >= _HIGH and gen.score > doc.score:
            return KnowledgeRouteResult(
                QueryRoute.GENERAL_QUERY,
                gen.score,
                "deterministic_general",
                gen.signals,
                document_score=doc.score,
                general_score=gen.score,
            )

        if doc.score >= _MILD and doc.score >= gen.score:
            return KnowledgeRouteResult(
                QueryRoute.DOCUMENT_QUERY,
                doc.score,
                "deterministic_document_mild",
                doc.signals,
                document_score=doc.score,
                general_score=gen.score,
            )
        if gen.score >= _MILD and gen.score > doc.score:
            return KnowledgeRouteResult(
                QueryRoute.GENERAL_QUERY,
                gen.score,
                "deterministic_general_mild",
                gen.signals,
                document_score=doc.score,
                general_score=gen.score,
            )

        if self._llm_provider is not None:
            llm_result = self._classify_with_llm(query)
            if llm_result is not None:
                return KnowledgeRouteResult(
                    route=llm_result.route,
                    confidence=llm_result.confidence,
                    method=llm_result.method,
                    signals=llm_result.signals,
                    document_score=doc.score,
                    general_score=gen.score,
                )

        return KnowledgeRouteResult(
            QueryRoute.DOCUMENT_QUERY,
            0.4,
            "default_document_safe",
            ("ambiguous_default",) + doc.signals + gen.signals,
            document_score=doc.score,
            general_score=gen.score,
        )

    def _classify_with_llm(self, query: str) -> KnowledgeRouteResult | None:
        assert self._llm_provider is not None
        user = (
            f"User message:\n{query.strip()}\n\n"
            "Label (DOCUMENT_QUERY or GENERAL_QUERY only):"
        )
        prompt = BuiltPrompt(
            system=_CLASSIFIER_SYSTEM,
            user=user,
            messages=[
                {"role": "system", "content": _CLASSIFIER_SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        request = LLMGenerationRequest(
            question=query.strip(),
            retrieved_chunks=[],
            conversation_history=None,
            prompt=prompt,
        )
        try:
            result = self._llm_provider.generate_sync(request)
        except Exception as exc:
            log_with_fields(
                logger,
                logging.WARNING,
                "Knowledge-route LLM classifier failed; using safe document default",
                reason=type(exc).__name__,
            )
            return None

        label = _parse_route_label(result.answer)
        if label is None:
            log_with_fields(
                logger,
                logging.WARNING,
                "Knowledge-route LLM classifier returned unparseable label",
                raw_answer=(result.answer or "")[:80],
            )
            return None

        return KnowledgeRouteResult(
            route=label,
            confidence=0.7,
            method="llm_classifier",
            signals=("llm_label",),
        )


def _parse_route_label(raw: str) -> QueryRoute | None:
    text = (raw or "").strip().upper()
    compact = re.sub(r"[^A-Z_]", "", text.replace(" ", "_"))
    if "DOCUMENT_QUERY" in compact or compact == "DOCUMENT":
        return QueryRoute.DOCUMENT_QUERY
    if "GENERAL_QUERY" in compact or compact == "GENERAL":
        return QueryRoute.GENERAL_QUERY
    first = compact.splitlines()[0] if compact else ""
    if first.startswith("DOCUMENT"):
        return QueryRoute.DOCUMENT_QUERY
    if first.startswith("GENERAL"):
        return QueryRoute.GENERAL_QUERY
    return None
