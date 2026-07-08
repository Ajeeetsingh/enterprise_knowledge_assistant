"""Unit tests for semantic retrieval matching."""

from __future__ import annotations

from app.evaluation.schemas import Difficulty, EvaluationCase
from app.evaluation.semantic_matcher import (
    evaluate_semantic_match,
    is_semantically_relevant,
    resolve_semantic_expectation,
)
from app.rag.types import RetrievalResult


def _case(**overrides) -> EvaluationCase:
    defaults = {
        "id": "CASE-1",
        "question": "What is the company headquarters?",
        "expected_answer": "Singapore",
        "expected_document": "doc.pdf",
        "expected_page": 9,
        "expected_chunks": [21],
        "difficulty": Difficulty.EASY,
        "notes": "Singapore (HQ) is the headquarters location for GlobalTrust.",
    }
    defaults.update(overrides)
    return EvaluationCase(**defaults)


def _result(**overrides) -> RetrievalResult:
    defaults = {
        "content": "Singapore (HQ) is the headquarters location for GlobalTrust.",
        "source": "doc.pdf",
        "category": "general",
        "confidence": 0.5,
        "chunk_id": "doc.pdf::sem-h15-p16",
        "page_number": 9,
        "page_start": 9,
        "page_end": 9,
        "section_title": "Corporate Overview",
    }
    defaults.update(overrides)
    return RetrievalResult(**defaults)


def test_resolve_semantic_expectation_uses_notes_fallback() -> None:
    expectation = resolve_semantic_expectation(_case())
    assert expectation.document == "doc.pdf"
    assert expectation.page_start == 9
    assert "Singapore" in expectation.semantic_region


def test_semantic_match_accepts_non_legacy_chunk_id() -> None:
    assert is_semantically_relevant(_result(), _case()) is True


def test_semantic_match_requires_document_match() -> None:
    assert is_semantically_relevant(_result(source="other.pdf"), _case()) is False


def test_semantic_match_requires_page_overlap() -> None:
    assert is_semantically_relevant(_result(page_number=20, page_start=20, page_end=20), _case()) is False


def test_semantic_match_accepts_adjacent_page_with_same_content() -> None:
    assert is_semantically_relevant(_result(page_number=10, page_start=10, page_end=10), _case()) is True


def test_semantic_match_uses_section_title_when_provided() -> None:
    case = _case(expected_section_title="Corporate Overview")
    assert is_semantically_relevant(_result(), case) is True
    assert is_semantically_relevant(_result(section_title="Financial Results"), case) is False


def test_semantic_match_uses_hierarchy_path_when_provided() -> None:
    case = _case(expected_hierarchy_path=("Corporate Overview", "Headquarters"))
    assert is_semantically_relevant(
        _result(hierarchy_path=("Corporate Overview", "Headquarters", "Details")),
        case,
    ) is True


def test_semantic_match_reports_reasons() -> None:
    match = evaluate_semantic_match(_result(), _case())
    assert match.is_relevant is True
    assert "document_match" in match.reasons
    assert "semantic_region_match" in match.reasons
