"""Query routing types for product-help vs document RAG vs general answers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from app.query_router.document_catalog import DocumentRouteCatalog
from app.query_router.route_signals import RouteSignalContext

if TYPE_CHECKING:
    from app.query_router.conversation_hints import ConversationRouteHints


class QueryRoute(StrEnum):
    """Top-level assistant route."""

    PRODUCT_HELP = "product_help"
    DOCUMENT_QUERY = "document_query"
    GENERAL_QUERY = "general_query"
    UNSAFE = "unsafe"


@dataclass(frozen=True)
class UserQueryContext:
    """Request-scoped facts used to tailor routing and product-help answers."""

    role_name: str
    can_upload: bool
    has_accessible_documents: bool
    accessible_document_count: int = 0
    """Optional prior-turn hints for follow-up routing (never used for ACL)."""
    conversation_hints: "ConversationRouteHints | None" = None
    """True for the public guest demo — never grants document access."""
    is_guest: bool = False
    """Configurable tenant aliases (never hardcoded customer names in code)."""
    org_aliases: tuple[str, ...] = ()
    """Authorized document filenames/titles for data-driven DOCUMENT signals."""
    document_catalog: DocumentRouteCatalog = field(default_factory=DocumentRouteCatalog)
    """When False, skip embedding-based enterprise-intent matching."""
    enable_semantic_enterprise_intent: bool = True

    def to_signal_context(self) -> RouteSignalContext:
        """Build classifier signal context from this request."""
        return RouteSignalContext(
            has_accessible_documents=self.has_accessible_documents,
            org_aliases=self.org_aliases,
            catalog=self.document_catalog,
            enable_semantic_enterprise_intent=self.enable_semantic_enterprise_intent,
        )


@dataclass(frozen=True)
class RouteDecision:
    """Outcome of query classification (and optional curated answer)."""

    route: QueryRoute
    confidence: float
    intent_id: str | None = None
    answer: str | None = None
    message: str = ""
    """Internal answer kind: product_help | document_grounded | general | …"""
    answer_kind: str | None = None
    classification_method: str | None = None

    @property
    def should_skip_rag(self) -> bool:
        """True when RAG must not run (product/general/unsafe or curated answer)."""
        if self.route == QueryRoute.PRODUCT_HELP and bool(self.answer and self.answer.strip()):
            return True
        if self.route == QueryRoute.GENERAL_QUERY:
            return True
        if self.route == QueryRoute.UNSAFE and bool(self.answer and self.answer.strip()):
            return True
        if self.route == QueryRoute.DOCUMENT_QUERY and bool(self.answer and self.answer.strip()):
            return True
        return False
