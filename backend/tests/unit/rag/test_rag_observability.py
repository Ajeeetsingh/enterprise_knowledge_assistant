"""Unit tests for Phase-2B RAG observability (diagnostics only)."""

from __future__ import annotations

from types import SimpleNamespace

from app.rag.observability.expected import (
    ExpectedSignature,
    evaluate_expected_chunks,
    find_expected_chunk,
    select_expectation_key,
)
from app.rag.observability.models import chunk_preview
from app.rag.observability.reporter import render_diagnostic_report
from app.rag.observability.models import RagDiagnosticReport, ExpectedChunkVerdict


def test_chunk_preview_truncates() -> None:
    text = "x" * 500
    preview = chunk_preview(text, limit=100)
    assert len(preview) <= 101
    assert preview.endswith("…")


def test_select_expectation_key() -> None:
    assert select_expectation_key("What is the mission?") == "mission"
    assert select_expectation_key("metadata categories") == "metadata"
    assert select_expectation_key("taxonomy hierarchy") == "taxonomy"
    assert select_expectation_key("unrelated question") is None


def test_find_expected_chunk_prefers_source() -> None:
    chunks = [
        SimpleNamespace(
            chunk_id="a",
            source="other.pdf",
            page_number=1,
            content="1.4 Mission Apex National Bank exists to serve clients.",
        ),
        SimpleNamespace(
            chunk_id="b",
            source="COMPANY_PROFILE.pdf",
            page_number=6,
            content="1.4 Mission Apex National Bank exists to serve clients.",
        ),
    ]
    sig = ExpectedSignature(
        label="Mission",
        must_contain=("1.4 mission",),
        preferred_source_substr=("company_profile",),
    )
    match = find_expected_chunk(chunks, sig)
    assert match is not None
    assert match.chunk_id == "b"


def test_evaluate_expected_fates() -> None:
    chunks = [
        SimpleNamespace(
            chunk_id="mission-1",
            source="COMPANY_PROFILE.pdf",
            page_number=6,
            content="1.4 Mission Apex National Bank exists to serve.",
        ),
        SimpleNamespace(
            chunk_id="values-1",
            source="COMPANY_PROFILE.pdf",
            page_number=10,
            content="1.6 Core Values Client Stewardship comes first.",
        ),
    ]
    # Never retrieved
    verdicts = evaluate_expected_chunks(
        question="What is the mission and core values?",
        indexed_chunks=chunks,
        stages={"dense": [], "bm25": [], "fusion": [], "per_query": []},
        final_chunk_ids=[],
        rerank_chunk_ids=[],
        merge_chunk_ids=[],
    )
    assert any(v.fate == "never_retrieved" for v in verdicts)

    # Found in final
    verdicts = evaluate_expected_chunks(
        question="What is the mission and core values?",
        indexed_chunks=chunks,
        stages={
            "dense": ["values-1"],
            "bm25": [],
            "fusion": ["values-1"],
            "per_query": ["values-1"],
        },
        final_chunk_ids=["values-1"],
        rerank_chunk_ids=["values-1"],
        merge_chunk_ids=["values-1"],
    )
    values = next(v for v in verdicts if "Core values" in v.label)
    assert values.retrieved is True
    assert values.fate == "found_in_final_context"
    assert values.best_rank == 1


def test_render_diagnostic_report_contains_sections() -> None:
    report = RagDiagnosticReport(
        question="What is the mission?",
        expansion_queries=["mission", "vision"],
        expected_chunk_verdicts=[
            ExpectedChunkVerdict(
                label="Mission statement",
                signature="mission + steward",
                expected_chunk_id="c1",
                expected_document="COMPANY_PROFILE.pdf",
                expected_page=6,
                expected_preview="Mission...",
                retrieved=False,
                best_rank=None,
                fate="never_retrieved",
            )
        ],
        final_answer="I don't know.",
        answer_kind="llm",
    )
    text = render_diagnostic_report(report)
    assert "QUESTION" in text
    assert "FINAL CONTEXT" in text
    assert "MISSING / EXPECTED CHUNK DETECTION" in text
    assert "never_retrieved" in text
