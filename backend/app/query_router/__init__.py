"""Intelligent query routing above the secure RAG pipeline.

Classifies questions into product-help, document knowledge, general, and
unsafe routes without modifying ``EnterpriseRAG`` authorization.
"""

from app.query_router.conversation_hints import (
    ConversationRouteHints,
    infer_route_hints,
    looks_like_follow_up,
)
from app.query_router.general_responder import (
    GENERAL_HISTORY_MAX_CHARS,
    GENERAL_HISTORY_MAX_MESSAGES,
    GeneralQueryResponder,
    format_general_conversation_history,
)
from app.query_router.knowledge_classifier import KnowledgeRouteClassifier, KnowledgeRouteResult
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
from app.query_router.product_intents import PRODUCT_INTENTS, ProductIntent
from app.query_router.product_matcher import (
    DEFAULT_SEMANTIC_THRESHOLD,
    ProductIntentMatcher,
    ProductMatch,
    normalize_query,
)
from app.query_router.router import QueryRouter, get_query_router
from app.query_router.safety import UNSAFE_BOUNDARY_MESSAGE, assess_unsafe_intent
from app.query_router.types import QueryRoute, RouteDecision, UserQueryContext

__all__ = [
    "ANSWER_KIND_DOCUMENT_GROUNDED",
    "ANSWER_KIND_DOCUMENT_INSUFFICIENT",
    "ANSWER_KIND_DOCUMENT_UNAVAILABLE",
    "ANSWER_KIND_GENERAL",
    "ANSWER_KIND_PRODUCT_HELP",
    "ANSWER_KIND_UNSAFE",
    "ConversationRouteHints",
    "DEFAULT_SEMANTIC_THRESHOLD",
    "GENERAL_HISTORY_MAX_CHARS",
    "GENERAL_HISTORY_MAX_MESSAGES",
    "INSUFFICIENT_DOCUMENT_EVIDENCE_MESSAGE",
    "PRODUCT_INTENTS",
    "UNSAFE_BOUNDARY_MESSAGE",
    "ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE",
    "GeneralQueryResponder",
    "KnowledgeRouteClassifier",
    "KnowledgeRouteResult",
    "ProductIntent",
    "ProductIntentMatcher",
    "ProductMatch",
    "QueryRoute",
    "QueryRouter",
    "RouteDecision",
    "UserQueryContext",
    "assess_unsafe_intent",
    "format_general_conversation_history",
    "get_query_router",
    "infer_route_hints",
    "looks_like_follow_up",
    "normalize_query",
]
