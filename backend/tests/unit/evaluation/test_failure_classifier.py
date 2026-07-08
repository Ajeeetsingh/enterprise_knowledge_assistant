"""Unit tests for failure classification."""

from __future__ import annotations

from app.evaluation.failure_classifier import classify_failures
from app.evaluation.schemas import (
    AnswerEvaluationResult,
    AnswerMatchMode,
    CitationEvaluationResult,
    Difficulty,
    EvaluationCase,
    FailureType,
    QuestionResult,
    RetrievalEvaluationResult,
)


def _make_case() -> EvaluationCase:
    return EvaluationCase(
        id="CASE-1",
        question="What is the company headquarters?",
        expected_answer="Singapore",
        expected_document="doc.pdf",
        expected_chunks=[21],
        difficulty=Difficulty.EASY,
    )


def _make_result(**overrides) -> QuestionResult:
    defaults = {
        "case_id": "CASE-1",
        "question": "What is the company headquarters?",
        "difficulty": "easy",
        "document_type": "overview",
        "query_category": "factual_lookup",
        "tags": [],
        "retrieval": RetrievalEvaluationResult(
            retrieved_documents=["doc.pdf"],
            retrieved_chunks=[0],
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
            failure_reason="expected_chunk_not_in_top_k",
        ),
        "answer": AnswerEvaluationResult(
            mode=AnswerMatchMode.CONTAINS,
            passed=False,
            actual_answer="London",
            expected_answer="Singapore",
            detail="",
        ),
        "citation": CitationEvaluationResult(
            passed=False,
            expected_citations=[],
            actual_citations=[],
            detail="",
        ),
        "retrieval_latency_ms": 1.0,
        "generation_latency_ms": 1.0,
        "total_latency_ms": 2.0,
        "retrieval_confidence": 0.2,
        "routed_category": "general",
        "access_granted": True,
        "context_precision": 0.0,
        "hallucination_detected": True,
    }
    defaults.update(overrides)
    return QuestionResult(**defaults)


def test_classify_retrieval_and_generation_failures() -> None:
    failures = classify_failures(_make_case(), _make_result())
    assert FailureType.RETRIEVAL_FAILURE in failures
    assert FailureType.GENERATION_FAILURE in failures
    assert FailureType.CITATION_FAILURE in failures
    assert FailureType.HALLUCINATION in failures


def test_classify_rbac_filtering() -> None:
    result = _make_result(access_granted=False)
    failures = classify_failures(_make_case(), result)
    assert failures == [FailureType.RBAC_FILTERING]
