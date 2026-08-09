"""Unit tests for list-context assembly and retrieval top-k resolution."""

from __future__ import annotations

from app.rag.engine import (
    _expand_exhaustive_context,
    _resolve_context_top_k,
)
from app.rag.query_processing.schemas import QueryCategory
from app.rag.types import RetrievalResult


def _chunk(chunk_id: str, source: str, content: str = "body") -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="executive",
        confidence=0.5,
        chunk_id=chunk_id,
    )


class TestResolveContextTopK:
    def test_list_queries_use_larger_context_window(self) -> None:
        assert _resolve_context_top_k(QueryCategory.LIST) >= 8

    def test_general_queries_use_configured_default(self) -> None:
        assert _resolve_context_top_k(QueryCategory.GENERAL) == 5

    def test_explicit_override_wins(self) -> None:
        assert _resolve_context_top_k(QueryCategory.LIST, explicit_top_k=3) == 3


class TestExpandExhaustiveContext:
    def test_preserves_rerank_order_for_generic_list_queries(self) -> None:
        """Non-exec/strategic LIST queries must keep CrossEncoder order."""
        reranked = [
            _chunk("meta-toc", "002_ENTERPRISE_METADATA_STANDARD.pdf", "4.1 Administrative"),
            _chunk("risk-a", "GTFS-RISK-001_Enterprise_Risk_Management_Framework.pdf"),
            _chunk("hr-a", "GTFS-HR-001_Employee_Handbook.pdf"),
        ]
        candidates = reranked + [
            _chunk("meta-late", "002_ENTERPRISE_METADATA_STANDARD.pdf", "8.1 Document Owner"),
        ]

        expanded = _expand_exhaustive_context(
            reranked,
            candidates,
            top_k=3,
            category=QueryCategory.LIST,
            query="What are the different categories of metadata?",
        )

        assert [item.chunk_id for item in expanded] == [
            "meta-toc",
            "risk-a",
            "hr-a",
        ]

    def test_adds_same_source_chunks_for_executive_list_queries(self) -> None:
        reranked = [
            _chunk("exec-a", "GTFS-EXEC-001_Company_Overview.pdf", "Sarah Mitchell"),
            _chunk("risk-a", "GTFS-RISK-001_Enterprise_Risk_Management_Framework.pdf"),
            _chunk("hr-a", "GTFS-HR-001_Employee_Handbook.pdf"),
        ]
        candidates = reranked + [
            _chunk("exec-b", "GTFS-EXEC-001_Company_Overview.pdf", "Daniel Carter"),
            _chunk("exec-c", "GTFS-EXEC-001_Company_Overview.pdf", "Michael Rodriguez"),
        ]

        expanded = _expand_exhaustive_context(
            reranked,
            candidates,
            top_k=4,
            category=QueryCategory.LIST,
            query="List ALL executive leaders.",
        )

        assert [item.chunk_id for item in expanded] == [
            "exec-a",
            "exec-b",
            "exec-c",
            "risk-a",
        ]

    def test_no_expansion_for_general_queries(self) -> None:
        reranked = [
            _chunk("exec-a", "GTFS-EXEC-001_Company_Overview.pdf"),
            _chunk("risk-a", "GTFS-RISK-001_Enterprise_Risk_Management_Framework.pdf"),
        ]
        candidates = reranked + [
            _chunk("exec-b", "GTFS-EXEC-001_Company_Overview.pdf"),
        ]

        expanded = _expand_exhaustive_context(
            reranked,
            candidates,
            top_k=2,
            category=QueryCategory.GENERAL,
        )

        assert [item.chunk_id for item in expanded] == ["exec-a", "risk-a"]

    def test_executive_query_deprioritizes_strategic_sections(self) -> None:
        reranked = [
            _chunk(
                "exec-table",
                "GTFS-EXEC-001_Company_Overview.pdf",
                "Sarah Mitchell Chief Executive Officer",
            ),
        ]
        candidates = reranked + [
            _chunk(
                "exec-ciso",
                "GTFS-EXEC-001_Company_Overview.pdf",
                "Priya Raman Chief Information Security Officer",
            ),
            _chunk(
                "strategic",
                "GTFS-EXEC-001_Company_Overview.pdf",
                "7 Strategic Priorities for FY2026",
            ),
        ]

        expanded = _expand_exhaustive_context(
            reranked,
            candidates,
            top_k=2,
            category=QueryCategory.LIST,
            query="List ALL executive leaders.",
        )

        assert {item.chunk_id for item in expanded} == {"exec-table", "exec-ciso"}
