"""Unit tests for benchmark report generation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.evaluation.history import compare_reports, save_benchmark_report
from app.evaluation.report import (
    export_csv_report,
    export_json_report,
    export_summary_csv,
    render_console_summary,
    report_from_dict,
)
from app.evaluation.schemas import (
    AggregateMetrics,
    AnswerEvaluationResult,
    AnswerMatchMode,
    BenchmarkReport,
    CitationEvaluationResult,
    QuestionResult,
    RetrievalEvaluationResult,
)


def _sample_report() -> BenchmarkReport:
    retrieval = RetrievalEvaluationResult(
        retrieved_documents=["doc.pdf"],
        retrieved_chunks=[21],
        retrieved_pages=[9],
        similarity_scores=[0.25],
        expected_chunk_found=True,
        expected_rank=1,
        mrr_contribution=1.0,
        recall_at_1=True,
        recall_at_3=True,
        recall_at_5=True,
        precision_at_k=1.0,
        top_k_details=[],
    )
    question = QuestionResult(
        case_id="GTFS-001",
        question="What is the company headquarters?",
        difficulty="easy",
        document_type="overview",
        query_category="factual_lookup",
        tags=["hq"],
        retrieval=retrieval,
        answer=AnswerEvaluationResult(
            mode=AnswerMatchMode.CONTAINS,
            passed=True,
            actual_answer="Singapore",
            expected_answer="Singapore",
            detail="ok",
        ),
        citation=CitationEvaluationResult(
            passed=True,
            expected_citations=[],
            actual_citations=[{"source": "doc.pdf", "page": 8, "confidence": 0.25}],
            detail="ok",
        ),
        retrieval_latency_ms=12.5,
        generation_latency_ms=8.2,
        total_latency_ms=20.7,
        retrieval_confidence=0.25,
        routed_category="general",
        access_granted=True,
        generation_backend="answer_generator",
    )
    return BenchmarkReport(
        run_id="run-123",
        started_at=datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 4, 12, 0, 5, tzinfo=UTC),
        dataset_version="1.0.0",
        dataset_path="golden_dataset.json",
        corpus_path="../data",
        role="admin",
        retrieval_top_k=5,
        answer_match_mode=AnswerMatchMode.CONTAINS,
        metrics=AggregateMetrics(
            case_count=1,
            recall_at_1=1.0,
            recall_at_3=1.0,
            recall_at_5=1.0,
            mrr=1.0,
            precision_at_k=1.0,
            citation_accuracy=1.0,
            answer_accuracy=1.0,
            top_1_correct_pct=1.0,
            top_3_correct_pct=1.0,
            avg_retrieval_confidence=0.25,
            avg_retrieval_latency_ms=12.5,
            avg_generation_latency_ms=8.2,
            avg_total_latency_ms=20.7,
            p50_total_latency_ms=20.7,
            p95_total_latency_ms=20.7,
            context_precision=0.8,
            hallucination_rate=0.0,
        ),
        question_results=[question],
        failure_analysis=[],
        failure_type_analysis=[],
        dataset_breakdown=None,
        worst_performing=[],
        metadata={"total_chunks": 25},
    )


def test_report_round_trip_serialization() -> None:
    report = _sample_report()
    restored = report_from_dict(report.to_dict())
    assert restored.run_id == report.run_id
    assert restored.metrics.recall_at_1 == 1.0
    assert restored.question_results[0].case_id == "GTFS-001"


def test_render_console_summary_contains_key_metrics() -> None:
    summary = render_console_summary(_sample_report())
    assert "Recall@1" in summary
    assert "Answer Accuracy" in summary
    assert "GTFS-001" in summary


def test_export_json_and_csv(tmp_path: Path) -> None:
    report = _sample_report()
    json_path = export_json_report(report, tmp_path / "report.json")
    csv_path = export_csv_report(report, tmp_path / "report.csv")
    summary_path = export_summary_csv(report, tmp_path / "summary.csv")

    assert json_path.exists()
    assert csv_path.exists()
    assert summary_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["metrics"]["mrr"] == 1.0


def test_save_benchmark_report_and_compare(tmp_path: Path) -> None:
    baseline = _sample_report()
    baseline.metrics = AggregateMetrics(
        case_count=1,
        recall_at_1=0.6,
        recall_at_3=0.8,
        recall_at_5=0.8,
        mrr=0.7,
        precision_at_k=0.5,
        citation_accuracy=0.5,
        answer_accuracy=0.5,
        top_1_correct_pct=0.6,
        top_3_correct_pct=0.8,
        avg_retrieval_confidence=0.2,
        avg_retrieval_latency_ms=10.0,
        avg_generation_latency_ms=10.0,
        avg_total_latency_ms=20.0,
        p50_total_latency_ms=20.0,
        p95_total_latency_ms=20.0,
        context_precision=0.5,
        hallucination_rate=0.1,
    )
    current = _sample_report()

    save_benchmark_report(baseline, results_dir=tmp_path)
    save_benchmark_report(current, results_dir=tmp_path)

    comparison = compare_reports(baseline, current)
    recall_delta = next(
        item for item in comparison.deltas if item.metric == "recall_at_1"
    )
    assert recall_delta.before == 0.6
    assert recall_delta.after == 1.0
    assert recall_delta.delta == pytest.approx(0.4)
