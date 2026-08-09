"""Regression tests: enterprise questions must route to DOCUMENT_QUERY (RAG).

Tenant-agnostic: uses configurable org aliases + authorized document catalog
+ semantic enterprise intent. Never requires hardcoded customer names in
production routing code.
"""

from __future__ import annotations

import pytest

from app.query_router import QueryRoute, QueryRouter, UserQueryContext
from app.query_router.document_catalog import build_document_route_catalog
from app.query_router.knowledge_classifier import KnowledgeRouteClassifier
from app.query_router.route_signals import RouteSignalContext


def _sample_catalog() -> object:
    """Simulate an uploaded enterprise corpus (filenames only — no hardcoding in app)."""
    return build_document_route_catalog(
        frozenset(
            {
                "00_foundation/COMPANY_PROFILE.md",
                "01_enterprise_governance/002_ENTERPRISE_METADATA_STANDARD.md",
                "01_enterprise_governance/003_KNOWLEDGE_TAXONOMY.md",
                "01_enterprise_governance/004_COMMITTEE_CHARTER.md",
                "03_finance/008_FINANCE_APPROVAL_AUTHORITY_MATRIX.md",
            }
        )
    )


def _ctx(
    *,
    has_docs: bool = True,
    org_aliases: tuple[str, ...] = (),
    enable_semantic: bool = True,
) -> UserQueryContext:
    catalog = _sample_catalog() if has_docs else build_document_route_catalog(frozenset())
    return UserQueryContext(
        role_name="Admin",
        can_upload=True,
        has_accessible_documents=has_docs,
        accessible_document_count=len(catalog.filenames),
        org_aliases=org_aliases,
        document_catalog=catalog,
        enable_semantic_enterprise_intent=enable_semantic,
    )


@pytest.fixture(scope="module")
def router() -> QueryRouter:
    matcher = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
    matcher.match_and_answer.return_value = None
    return QueryRouter(
        product_matcher=matcher,
        knowledge_classifier=KnowledgeRouteClassifier(llm_provider=None),
        llm_provider=False,
    )


DOCUMENT_CASES = [
    "What is Apex National Bank's mission?",
    "Explain the Enterprise Knowledge Taxonomy.",
    "What does the Company Profile say about approval authority?",
    "Explain our metadata standard.",
    "Describe the committee governance structure.",
    "What is Apex National Bank's mission, vision, and core values?",
    "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
    "Explain the hierarchy used in the Enterprise Knowledge Taxonomy.",
    "What are the company's ethical principles?",
]

GENERAL_CASES = [
    "Explain EBITDA.",
    "Write me a resignation email.",
    "What is Python?",
    "Summarize this paragraph.",
    "Tell me a joke.",
]


@pytest.mark.parametrize("question", DOCUMENT_CASES)
def test_enterprise_questions_route_to_document(router: QueryRouter, question: str) -> None:
    # Aliases come from tenant config in production; tests supply them explicitly.
    decision = router.route(
        question,
        _ctx(org_aliases=("Apex National Bank", "ANB", "Apex")),
    )
    assert decision.route == QueryRoute.DOCUMENT_QUERY, (
        f"{question!r} routed to {decision.route} via {decision.classification_method}"
    )
    assert not decision.should_skip_rag


@pytest.mark.parametrize("question", GENERAL_CASES)
def test_general_questions_stay_general(router: QueryRouter, question: str) -> None:
    decision = router.route(
        question,
        _ctx(org_aliases=("Apex National Bank", "ANB", "Apex")),
    )
    assert decision.route == QueryRoute.GENERAL_QUERY, (
        f"{question!r} routed to {decision.route} via {decision.classification_method}"
    )
    assert decision.should_skip_rag


def test_catalog_alone_routes_taxonomy_without_org_alias(router: QueryRouter) -> None:
    """Filename/title overlap must work without customer-specific aliases."""
    decision = router.route(
        "Explain the Knowledge Taxonomy hierarchy.",
        _ctx(org_aliases=(), enable_semantic=False),
    )
    assert decision.route == QueryRoute.DOCUMENT_QUERY


def test_semantic_enterprise_intent_without_alias_or_title_hit(router: QueryRouter) -> None:
    """Ethical principles should prefer DOCUMENT via semantic intent when docs exist."""
    decision = router.route(
        "What are the company's ethical principles?",
        _ctx(org_aliases=(), enable_semantic=True),
    )
    assert decision.route == QueryRoute.DOCUMENT_QUERY


def test_classifier_scores_exposed_for_debug() -> None:
    clf = KnowledgeRouteClassifier(llm_provider=None)
    result = clf.classify(
        "Explain EBITDA.",
        RouteSignalContext(has_accessible_documents=True, enable_semantic_enterprise_intent=True),
    )
    assert result.route == QueryRoute.GENERAL_QUERY
    assert result.general_score >= result.document_score
