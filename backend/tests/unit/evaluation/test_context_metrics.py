"""Unit tests for context precision and hallucination metrics."""

from __future__ import annotations

from app.evaluation.metrics import (
    compute_context_precision,
    detect_hallucination,
)
from app.evaluation.schemas import Difficulty, EvaluationCase
from app.rag.types import RetrievalResult


def _case() -> EvaluationCase:
    return EvaluationCase(
        id="CASE-1",
        question="What is the company headquarters?",
        expected_answer="Singapore",
        expected_document="doc.pdf",
        expected_chunks=[21],
        expected_page=9,
        notes="Singapore (HQ) is the headquarters.",
        difficulty=Difficulty.EASY,
    )


def _result(chunk_index: int, content: str, *, page_number: int = 9) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source="doc.pdf",
        category="general",
        confidence=0.5,
        chunk_id=f"doc.pdf::{chunk_index}",
        page_number=page_number,
        page_start=page_number,
        page_end=page_number,
    )


def test_context_precision_counts_relevant_chunks() -> None:
    results = [
        _result(21, "Singapore (HQ) is the headquarters."),
        _result(0, "Table of contents only.", page_number=1),
    ]
    precision = compute_context_precision(_case(), results)
    assert precision == 0.5


def test_hallucination_detects_unsupported_answer_tokens() -> None:
    results = [_result(21, "Singapore is the headquarters.")]
    detected = detect_hallucination(
        "The headquarters is located in London.",
        results,
        expected_answer="Singapore",
    )
    assert detected is True


def test_hallucination_not_detected_for_grounded_answer() -> None:
    results = [_result(21, "Singapore is the headquarters.")]
    detected = detect_hallucination(
        "The headquarters is in Singapore.",
        results,
        expected_answer="Singapore",
    )
    assert detected is False
