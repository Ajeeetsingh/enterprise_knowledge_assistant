"""Regression tests for Phase 2 retrieval authorization fail-closed behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.rag.engine import EnterpriseRAG


def test_empty_authorized_sources_does_not_become_unrestricted() -> None:
    """Empty frozenset must stay deny-all (never coerced to None)."""
    engine = EnterpriseRAG.__new__(EnterpriseRAG)
    engine._vector_store = None
    engine._retriever = MagicMock()

    metadata = MagicMock()
    metadata.search_semantic_retriever.return_value = []
    engine._metadata_retriever = metadata

    engine._search(
        "who are the issuers?",
        top_k=5,
        allowed_categories={"general"},
        authorized_sources=frozenset(),
    )

    kwargs = metadata.search_semantic_retriever.call_args.kwargs
    assert kwargs["allowed_sources"] == set()
    assert kwargs["allowed_sources"] is not None


def test_none_authorized_sources_still_means_no_filter() -> None:
    """Explicit None remains the CLI/eval path for unrestricted search."""
    engine = EnterpriseRAG.__new__(EnterpriseRAG)
    engine._vector_store = None
    engine._retriever = MagicMock()

    metadata = MagicMock()
    metadata.search_semantic_retriever.return_value = []
    engine._metadata_retriever = metadata

    engine._search(
        "who are the issuers?",
        top_k=5,
        allowed_categories={"general"},
        authorized_sources=None,
    )

    kwargs = metadata.search_semantic_retriever.call_args.kwargs
    assert kwargs["allowed_sources"] is None
