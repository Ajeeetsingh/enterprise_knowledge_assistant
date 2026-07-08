"""Unit tests for HTML dashboard generation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.evaluation.dashboard import export_html_dashboard, render_benchmark_dashboard
from app.evaluation.schemas import (
    AggregateMetrics,
    AnswerMatchMode,
    BenchmarkReport,
    FailureTypeSummary,
)


def _minimal_report() -> BenchmarkReport:
    return BenchmarkReport(
        run_id="dashboard-test-run",
        started_at=datetime(2026, 7, 4, 12, 0, 0, tzinfo=UTC),
        completed_at=datetime(2026, 7, 4, 12, 1, 0, tzinfo=UTC),
        dataset_version="2.0.0",
        dataset_path="golden_dataset_full.json",
        corpus_path="../data",
        role="admin",
        retrieval_top_k=5,
        answer_match_mode=AnswerMatchMode.CONTAINS,
        metrics=AggregateMetrics(
            case_count=144,
            recall_at_1=0.5,
            recall_at_3=0.7,
            recall_at_5=0.8,
            mrr=0.6,
            precision_at_k=0.3,
            citation_accuracy=0.4,
            answer_accuracy=0.55,
            top_1_correct_pct=0.5,
            top_3_correct_pct=0.7,
            avg_retrieval_confidence=0.45,
            avg_retrieval_latency_ms=15.0,
            avg_generation_latency_ms=2.0,
            avg_total_latency_ms=17.0,
            p50_total_latency_ms=16.0,
            p95_total_latency_ms=25.0,
            context_precision=0.42,
            hallucination_rate=0.12,
        ),
        question_results=[],
        failure_analysis=[],
        failure_type_analysis=[
            FailureTypeSummary(
                failure_type="retrieval_failure",
                count=10,
                case_ids=["A-001", "A-002"],
            )
        ],
        dataset_breakdown=None,
        worst_performing=["A-001"],
    )


def test_render_dashboard_contains_key_sections() -> None:
    html = render_benchmark_dashboard(_minimal_report())
    assert "Enterprise RAG Benchmark Dashboard" in html
    assert "Context Precision" in html
    assert "Hallucination Rate" in html
    assert "Failure Distribution" in html
    assert "retrieval_failure" in html


def test_export_html_dashboard_writes_file(tmp_path: Path) -> None:
    path = export_html_dashboard(_minimal_report(), tmp_path / "dashboard.html")
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
