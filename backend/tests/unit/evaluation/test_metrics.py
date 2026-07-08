"""Unit tests for retrieval benchmark metrics."""

from __future__ import annotations

import pytest

from app.evaluation.metrics import (
    aggregate_metrics,
    build_failure_analysis,
    build_retrieved_chunk_details,
    evaluate_citations,
    evaluate_retrieval,
    identify_worst_performing,
    parse_chunk_index,
)
from app.evaluation.schemas import (
    AnswerEvaluationResult,
    AnswerMatchMode,
    CitationEvaluationResult,
    Difficulty,
    EvaluationCase,
    ExpectedCitation,
    QuestionResult,
    RetrievalEvaluationResult,
)
from app.rag.types import Citation, RetrievalResult


def _question_result(**overrides) -> QuestionResult:
    defaults = {
        "case_id": "CASE",
        "question": "Q",
        "difficulty": "easy",
        "document_type": "overview",
        "query_category": "factual_lookup",
        "tags": [],
        "retrieval": RetrievalEvaluationResult(
            retrieved_documents=[],
            retrieved_chunks=[],
            retrieved_pages=[],
            similarity_scores=[],
            expected_chunk_found=False,
            expected_rank=None,
            mrr_contribution=0.0,
            recall_at_1=False,
            recall_at_3=False,
            recall_at_5=False,
            precision_at_k=0.0,
            top_k_details=[],
        ),
        "answer": AnswerEvaluationResult(
            mode=AnswerMatchMode.CONTAINS,
            passed=False,
            actual_answer="",
            expected_answer="",
            detail="",
        ),
        "citation": CitationEvaluationResult(
            passed=True,
            expected_citations=[],
            actual_citations=[],
            detail="",
        ),
        "retrieval_latency_ms": 1.0,
        "generation_latency_ms": 1.0,
        "total_latency_ms": 2.0,
        "retrieval_confidence": 0.0,
        "routed_category": "general",
        "access_granted": True,
    }
    defaults.update(overrides)
    return QuestionResult(**defaults)


def _make_case(**overrides) -> EvaluationCase:
    defaults = {
        "id": "CASE-1",
        "question": "What is the company headquarters?",
        "expected_answer": "Singapore",
        "expected_document": "doc.pdf",
        "expected_chunks": [21],
        "expected_page": 9,
        "notes": "Singapore (HQ) is the headquarters location for GlobalTrust.",
        "difficulty": Difficulty.EASY,
    }
    defaults.update(overrides)
    return EvaluationCase(**defaults)


def _make_result(
    chunk_index: int,
    confidence: float = 0.5,
    *,
    content: str | None = None,
    page_number: int = 9,
    chunk_id: str | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        content=content or "Singapore (HQ) is the headquarters location for GlobalTrust.",
        source="doc.pdf",
        category="general",
        confidence=confidence,
        chunk_id=chunk_id or f"doc.pdf::{chunk_index}",
        page_number=page_number,
        page_start=page_number,
        page_end=page_number,
    )


def test_parse_chunk_index() -> None:
    assert parse_chunk_index("doc.pdf::21") == 21
    assert parse_chunk_index("doc.pdf::sem-table-1") is None
    assert parse_chunk_index("invalid") is None


def test_evaluate_retrieval_semantic_rank_1() -> None:
    case = _make_case(expected_chunks=[21])
    results = [
        _make_result(21, chunk_id="doc.pdf::sem-h15-p16"),
        _make_result(0, content="Table of contents only.", page_number=1),
        _make_result(20, content="Unrelated section.", page_number=2),
    ]

    evaluation = evaluate_retrieval(case, results, retrieval_top_k=3)

    assert evaluation.semantic_match_found is True
    assert evaluation.expected_chunk_found is True
    assert evaluation.expected_rank == 1
    assert evaluation.recall_at_1 is True
    assert evaluation.recall_at_3 is True
    assert evaluation.recall_at_5 is True
    assert evaluation.mrr_contribution == 1.0
    assert evaluation.precision_at_k == pytest.approx(1 / 3)
    assert evaluation.legacy_chunk_match_found is False


def test_evaluate_retrieval_semantic_rank_2() -> None:
    case = _make_case(expected_chunks=[21])
    results = [
        _make_result(0, content="Table of contents only.", page_number=1),
        _make_result(21, chunk_id="doc.pdf::sem-h15-p16"),
    ]

    evaluation = evaluate_retrieval(case, results, retrieval_top_k=2)

    assert evaluation.expected_rank == 2
    assert evaluation.recall_at_1 is False
    assert evaluation.recall_at_3 is True
    assert evaluation.mrr_contribution == 0.5
    assert evaluation.failure_reason == "expected_semantic_region_not_rank_1"


def test_evaluate_retrieval_missing_semantic_region() -> None:
    case = _make_case(expected_chunks=[99])
    results = [
        _make_result(0, content="Table of contents only.", page_number=1),
        _make_result(1, content="Another unrelated section.", page_number=2),
    ]

    evaluation = evaluate_retrieval(case, results, retrieval_top_k=2)

    assert evaluation.semantic_match_found is False
    assert evaluation.expected_rank is None
    assert evaluation.mrr_contribution == 0.0
    assert evaluation.failure_reason == "expected_semantic_region_not_in_top_k"


def test_evaluate_citations_passes_with_expected_page() -> None:
    case = _make_case(
        expected_citations=[ExpectedCitation(source="doc.pdf", page=8)]
    )
    citations = [
        Citation(source="doc.pdf", excerpt="Singapore HQ", confidence=0.4, page=8)
    ]

    result = evaluate_citations(case, citations)
    assert result.passed is True


def test_evaluate_citations_fails_on_wrong_page() -> None:
    case = _make_case(
        expected_citations=[ExpectedCitation(source="doc.pdf", page=9)]
    )
    citations = [
        Citation(source="doc.pdf", excerpt="Singapore HQ", confidence=0.4, page=8)
    ]

    result = evaluate_citations(case, citations)
    assert result.passed is False


def test_aggregate_metrics() -> None:
    case = _make_case()
    retrieval_pass = RetrievalEvaluationResult(
        retrieved_documents=["doc.pdf"],
        retrieved_chunks=[],
        retrieved_pages=[9],
        similarity_scores=[0.4],
        expected_chunk_found=True,
        expected_rank=1,
        mrr_contribution=1.0,
        recall_at_1=True,
        recall_at_3=True,
        recall_at_5=True,
        precision_at_k=1.0,
        top_k_details=[],
        semantic_match_found=True,
    )
    retrieval_fail = RetrievalEvaluationResult(
        retrieved_documents=["doc.pdf"],
        retrieved_chunks=[],
        retrieved_pages=[1],
        similarity_scores=[0.2],
        expected_chunk_found=False,
        expected_rank=None,
        mrr_contribution=0.0,
        recall_at_1=False,
        recall_at_3=False,
        recall_at_5=False,
        precision_at_k=0.0,
        top_k_details=[],
        failure_reason="expected_semantic_region_not_in_top_k",
    )

    question_results = [
        _question_result(
            case_id="PASS",
            question=case.question,
            retrieval=retrieval_pass,
            answer=AnswerEvaluationResult(
                mode=AnswerMatchMode.CONTAINS,
                passed=True,
                actual_answer="Singapore",
                expected_answer="Singapore",
                detail="ok",
            ),
            retrieval_latency_ms=10.0,
            generation_latency_ms=20.0,
            total_latency_ms=30.0,
            retrieval_confidence=0.4,
        ),
        _question_result(
            case_id="FAIL",
            question=case.question,
            retrieval=retrieval_fail,
            answer=AnswerEvaluationResult(
                mode=AnswerMatchMode.CONTAINS,
                passed=False,
                actual_answer="London",
                expected_answer="Singapore",
                detail="fail",
            ),
            citation=CitationEvaluationResult(
                passed=False,
                expected_citations=[],
                actual_citations=[],
                detail="fail",
            ),
            retrieval_latency_ms=12.0,
            generation_latency_ms=18.0,
            total_latency_ms=30.0,
            retrieval_confidence=0.2,
        ),
    ]

    metrics = aggregate_metrics(question_results, retrieval_top_k=3)

    assert metrics.case_count == 2
    assert metrics.recall_at_1 == 0.5
    assert metrics.mrr == 0.5
    assert metrics.answer_accuracy == 0.5
    assert metrics.citation_accuracy == 0.5
    assert metrics.avg_total_latency_ms == 30.0


def test_build_failure_analysis_groups_reasons() -> None:
    question_results = [
        _question_result(
            case_id="A",
            retrieval=RetrievalEvaluationResult(
                retrieved_documents=[],
                retrieved_chunks=[],
                retrieved_pages=[],
                similarity_scores=[],
                expected_chunk_found=False,
                expected_rank=None,
                mrr_contribution=0.0,
                recall_at_1=False,
                recall_at_3=False,
                recall_at_5=False,
                precision_at_k=0.0,
                top_k_details=[],
                failure_reason="expected_semantic_region_not_in_top_k",
            ),
            answer=AnswerEvaluationResult(
                mode=AnswerMatchMode.CONTAINS,
                passed=False,
                actual_answer="x",
                expected_answer="y",
                detail="",
            ),
        )
    ]

    analysis = build_failure_analysis(question_results)
    reasons = {item.failure_reason: item.count for item in analysis}
    assert reasons["expected_semantic_region_not_in_top_k"] == 1
    assert reasons["answer_mismatch"] == 1


def test_identify_worst_performing() -> None:
    good = _question_result(
        case_id="GOOD",
        retrieval=RetrievalEvaluationResult(
            retrieved_documents=[],
            retrieved_chunks=[1],
            retrieved_pages=[1],
            similarity_scores=[0.5],
            expected_chunk_found=True,
            expected_rank=1,
            mrr_contribution=1.0,
            recall_at_1=True,
            recall_at_3=True,
            recall_at_5=True,
            precision_at_k=1.0,
            top_k_details=[],
            semantic_match_found=True,
        ),
        answer=AnswerEvaluationResult(
            mode=AnswerMatchMode.CONTAINS,
            passed=True,
            actual_answer="ok",
            expected_answer="ok",
            detail="",
        ),
        retrieval_confidence=0.5,
    )
    bad = _question_result(
        case_id="BAD",
        answer=AnswerEvaluationResult(
            mode=AnswerMatchMode.CONTAINS,
            passed=False,
            actual_answer="no",
            expected_answer="yes",
            detail="",
        ),
        citation=CitationEvaluationResult(
            passed=False,
            expected_citations=[],
            actual_citations=[],
            detail="",
        ),
    )

    worst = identify_worst_performing([good, bad], limit=1)
    assert worst == ["BAD"]


def test_build_retrieved_chunk_details_includes_semantic_flags() -> None:
    case = _make_case()
    results = [_make_result(3, confidence=0.33, chunk_id="doc.pdf::sem-table-1")]
    details = build_retrieved_chunk_details(results, case=case)
    assert len(details) == 1
    assert details[0].rank == 1
    assert details[0].chunk_index is None
    assert details[0].semantic_match is True
    assert details[0].legacy_chunk_match is False
