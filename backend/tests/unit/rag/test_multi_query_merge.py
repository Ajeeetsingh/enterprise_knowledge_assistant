"""Unit tests for multi-query merge reservation behaviour."""

from __future__ import annotations

from app.rag.query_processing.multi_query import merge_multi_query_results
from app.rag.types import RetrievalResult


def _hit(chunk_id: str, content: str, score: float) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source="doc.pdf",
        category="general",
        confidence=score,
        chunk_id=chunk_id,
        page_number=1,
        final_score=score,
    )


def test_merge_skips_cover_stubs_in_original_reservation() -> None:
    """Reserved original slots must not be consumed by org-name cover pages."""
    original = [
        _hit("cover_a", "Apex National Bank", 0.90),
        _hit("cover_b", "Apex National Bank", 0.90),
        _hit("core_heading", "1.6 Core Values", 0.89),
        _hit(
            "masthead",
            "Apex National Bank - Records Retention Policy "
            "Enterprise Governance Policy | Retention and Archival",
            0.88,
        ),
        _hit("purpose", "Document Purpose table with substantive rows and mappings.", 0.85),
        _hit("noise", "Apex National Bank", 0.84),
    ]
    expansion = [
        _hit("mission", "1.4 Mission To steward our clients' financial lives.", 0.70),
        _hit("vision", "1.5 Vision To be the most trusted bank.", 0.68),
        _hit("core_table", "Value Definition Observable Behaviour Integrity First ...", 0.66),
    ]
    merged = merge_multi_query_results([original, expansion], limit=6)
    ids = [item.chunk_id for item in merged]
    assert "cover_a" not in ids
    assert "cover_b" not in ids
    assert "noise" not in ids
    assert "masthead" not in ids
    assert "purpose" in ids
    assert "mission" in ids
    assert "vision" in ids
