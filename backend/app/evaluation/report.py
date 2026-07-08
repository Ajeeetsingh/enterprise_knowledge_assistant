"""Benchmark report generation and export."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

from app.evaluation.history import RegressionComparison
from app.evaluation.schemas import (
    AggregateMetrics,
    AnswerEvaluationResult,
    AnswerMatchMode,
    BenchmarkReport,
    CitationEvaluationResult,
    DatasetBreakdown,
    FailureSummary,
    FailureType,
    FailureTypeSummary,
    QuestionResult,
    RetrievalEvaluationResult,
    RetrievedChunkDetail,
)


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_retrieval(payload: dict[str, Any]) -> RetrievalEvaluationResult:
    top_k_details = [
        RetrievedChunkDetail(
            rank=int(item["rank"]),
            chunk_id=str(item["chunk_id"]),
            chunk_index=item.get("chunk_index"),
            source=str(item["source"]),
            page_number=item.get("page_number"),
            category=str(item["category"]),
            confidence=float(item["confidence"]),
            content_preview=str(item["content_preview"]),
        )
        for item in payload.get("top_k_details", [])
    ]
    return RetrievalEvaluationResult(
        retrieved_documents=[str(item) for item in payload.get("retrieved_documents", [])],
        retrieved_chunks=[int(item) for item in payload.get("retrieved_chunks", [])],
        retrieved_pages=payload.get("retrieved_pages", []),
        similarity_scores=[float(item) for item in payload.get("similarity_scores", [])],
        expected_chunk_found=bool(payload.get("expected_chunk_found", False)),
        expected_rank=payload.get("expected_rank"),
        mrr_contribution=float(payload.get("mrr_contribution", 0.0)),
        recall_at_1=bool(payload.get("recall_at_1", False)),
        recall_at_3=bool(payload.get("recall_at_3", False)),
        recall_at_5=bool(payload.get("recall_at_5", False)),
        precision_at_k=float(payload.get("precision_at_k", 0.0)),
        top_k_details=top_k_details,
        failure_reason=payload.get("failure_reason"),
    )


def _parse_answer(payload: dict[str, Any]) -> AnswerEvaluationResult:
    return AnswerEvaluationResult(
        mode=AnswerMatchMode(payload.get("mode", AnswerMatchMode.CONTAINS.value)),
        passed=bool(payload.get("passed", False)),
        actual_answer=str(payload.get("actual_answer", "")),
        expected_answer=str(payload.get("expected_answer", "")),
        detail=str(payload.get("detail", "")),
    )


def _parse_citation(payload: dict[str, Any]) -> CitationEvaluationResult:
    from app.evaluation.schemas import ExpectedCitation

    expected = [
        ExpectedCitation(source=str(item["source"]), page=item.get("page"))
        for item in payload.get("expected_citations", [])
    ]
    return CitationEvaluationResult(
        passed=bool(payload.get("passed", False)),
        expected_citations=expected,
        actual_citations=list(payload.get("actual_citations", [])),
        detail=str(payload.get("detail", "")),
    )


def report_from_dict(payload: dict[str, Any]) -> BenchmarkReport:
    """Deserialize a benchmark report from a JSON-compatible dictionary."""
    metrics_payload = payload["metrics"]
    metrics = AggregateMetrics(
        case_count=int(metrics_payload["case_count"]),
        recall_at_1=float(metrics_payload["recall_at_1"]),
        recall_at_3=float(metrics_payload["recall_at_3"]),
        recall_at_5=float(metrics_payload["recall_at_5"]),
        mrr=float(metrics_payload["mrr"]),
        precision_at_k=float(metrics_payload["precision_at_k"]),
        citation_accuracy=float(metrics_payload["citation_accuracy"]),
        answer_accuracy=float(metrics_payload["answer_accuracy"]),
        top_1_correct_pct=float(metrics_payload["top_1_correct_pct"]),
        top_3_correct_pct=float(metrics_payload["top_3_correct_pct"]),
        avg_retrieval_confidence=float(metrics_payload["avg_retrieval_confidence"]),
        avg_retrieval_latency_ms=float(metrics_payload["avg_retrieval_latency_ms"]),
        avg_generation_latency_ms=float(metrics_payload["avg_generation_latency_ms"]),
        avg_total_latency_ms=float(metrics_payload["avg_total_latency_ms"]),
        p50_total_latency_ms=float(metrics_payload["p50_total_latency_ms"]),
        p95_total_latency_ms=float(metrics_payload["p95_total_latency_ms"]),
        context_precision=float(metrics_payload.get("context_precision", 0.0)),
        hallucination_rate=float(metrics_payload.get("hallucination_rate", 0.0)),
    )

    question_results = [
        QuestionResult(
            case_id=str(item["case_id"]),
            question=str(item["question"]),
            difficulty=str(item["difficulty"]),
            document_type=str(item.get("document_type", "general")),
            query_category=str(item.get("query_category", "factual_lookup")),
            tags=[str(tag) for tag in item.get("tags", [])],
            retrieval=_parse_retrieval(item["retrieval"]),
            answer=_parse_answer(item["answer"]),
            citation=_parse_citation(item["citation"]),
            retrieval_latency_ms=float(item["retrieval_latency_ms"]),
            generation_latency_ms=float(item["generation_latency_ms"]),
            total_latency_ms=float(item["total_latency_ms"]),
            retrieval_confidence=float(item["retrieval_confidence"]),
            routed_category=str(item["routed_category"]),
            access_granted=bool(item["access_granted"]),
            context_precision=float(item.get("context_precision", 0.0)),
            hallucination_detected=bool(item.get("hallucination_detected", False)),
            failure_types=[
                FailureType(value) for value in item.get("failure_types", [])
            ],
            artifact_path=item.get("artifact_path"),
            generation_backend=item.get("generation_backend"),
        )
        for item in payload.get("question_results", [])
    ]

    failure_analysis = [
        FailureSummary(
            failure_reason=str(item["failure_reason"]),
            count=int(item["count"]),
            case_ids=[str(case_id) for case_id in item.get("case_ids", [])],
        )
        for item in payload.get("failure_analysis", [])
    ]

    failure_type_analysis = [
        FailureTypeSummary(
            failure_type=str(item["failure_type"]),
            count=int(item["count"]),
            case_ids=[str(case_id) for case_id in item.get("case_ids", [])],
        )
        for item in payload.get("failure_type_analysis", [])
    ]

    breakdown_payload = payload.get("dataset_breakdown")
    dataset_breakdown = None
    if breakdown_payload:
        dataset_breakdown = DatasetBreakdown(
            by_document_type=dict(breakdown_payload.get("by_document_type", {})),
            by_difficulty=dict(breakdown_payload.get("by_difficulty", {})),
            by_query_category=dict(breakdown_payload.get("by_query_category", {})),
        )

    return BenchmarkReport(
        run_id=str(payload["run_id"]),
        started_at=_parse_datetime(str(payload["started_at"])),
        completed_at=_parse_datetime(str(payload["completed_at"])),
        dataset_version=str(payload["dataset_version"]),
        dataset_path=str(payload["dataset_path"]),
        corpus_path=str(payload["corpus_path"]),
        role=str(payload["role"]),
        retrieval_top_k=int(payload["retrieval_top_k"]),
        answer_match_mode=AnswerMatchMode(payload["answer_match_mode"]),
        metrics=metrics,
        question_results=question_results,
        failure_analysis=failure_analysis,
        failure_type_analysis=failure_type_analysis,
        dataset_breakdown=dataset_breakdown,
        worst_performing=[str(item) for item in payload.get("worst_performing", [])],
        artifacts_dir=payload.get("artifacts_dir"),
        dashboard_path=payload.get("dashboard_path"),
        metadata=dict(payload.get("metadata", {})),
    )


def _format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_ms(value: float) -> str:
    return f"{value:.1f} ms"


def render_console_summary(
    report: BenchmarkReport,
    *,
    regression: RegressionComparison | None = None,
) -> str:
    """Render a human-readable benchmark summary."""
    lines: list[str] = []
    metrics = report.metrics

    lines.append("=" * 72)
    lines.append("RETRIEVAL BENCHMARK REPORT")
    lines.append("=" * 72)
    lines.append(f"Run ID:          {report.run_id}")
    lines.append(f"Dataset:         {report.dataset_version} ({report.dataset_path})")
    lines.append(f"Corpus:          {report.corpus_path}")
    lines.append(f"Cases:           {metrics.case_count}")
    lines.append(f"Retrieval top-K: {report.retrieval_top_k}")
    lines.append(f"Role:            {report.role}")
    lines.append("")
    lines.append("OVERALL METRICS")
    lines.append("-" * 72)
    lines.append(f"Recall@1:                 {_format_pct(metrics.recall_at_1)}")
    lines.append(f"Recall@3:                 {_format_pct(metrics.recall_at_3)}")
    lines.append(f"Recall@5:                 {_format_pct(metrics.recall_at_5)}")
    lines.append(f"MRR:                      {metrics.mrr:.3f}")
    lines.append(f"Precision@K:              {metrics.precision_at_k:.3f}")
    lines.append(f"Citation Accuracy:        {_format_pct(metrics.citation_accuracy)}")
    lines.append(f"Answer Accuracy:          {_format_pct(metrics.answer_accuracy)}")
    lines.append(f"Top-1 Correct %:          {_format_pct(metrics.top_1_correct_pct)}")
    lines.append(f"Top-3 Correct %:          {_format_pct(metrics.top_3_correct_pct)}")
    lines.append(f"Avg Retrieval Confidence: {metrics.avg_retrieval_confidence:.3f}")
    lines.append(f"Avg Retrieval Latency:    {_format_ms(metrics.avg_retrieval_latency_ms)}")
    lines.append(f"Avg Generation Latency:   {_format_ms(metrics.avg_generation_latency_ms)}")
    lines.append(f"Avg Total Latency:        {_format_ms(metrics.avg_total_latency_ms)}")
    lines.append(f"P50 Total Latency:        {_format_ms(metrics.p50_total_latency_ms)}")
    lines.append(f"P95 Total Latency:        {_format_ms(metrics.p95_total_latency_ms)}")
    lines.append(f"Context Precision:        {_format_pct(metrics.context_precision)}")
    lines.append(f"Hallucination Rate:       {_format_pct(metrics.hallucination_rate)}")

    if regression is not None:
        lines.append("")
        lines.append("REGRESSION COMPARISON")
        lines.append("-" * 72)
        for delta in regression.deltas:
            before = _format_pct(delta.before) if delta.metric.endswith("_pct") or "recall" in delta.metric or "accuracy" in delta.metric else f"{delta.before:.3f}"
            after = _format_pct(delta.after) if delta.metric.endswith("_pct") or "recall" in delta.metric or "accuracy" in delta.metric else f"{delta.after:.3f}"
            sign = "+" if delta.delta >= 0 else ""
            if "latency" in delta.metric:
                before = _format_ms(delta.before)
                after = _format_ms(delta.after)
                sign_delta = f"{sign}{delta.delta:.1f} ms"
            elif "recall" in delta.metric or "accuracy" in delta.metric or delta.metric.endswith("_pct"):
                sign_delta = f"{sign}{delta.delta * 100:.1f}%"
            else:
                sign_delta = f"{sign}{delta.delta:.3f}"
            lines.append(
                f"{delta.metric:24} {regression.baseline_label:8} {before:>10}  "
                f"{regression.comparison_label:8} {after:>10}  Delta {sign_delta}"
            )

    if report.failure_analysis:
        lines.append("")
        lines.append("FAILURE ANALYSIS")
        lines.append("-" * 72)
        for summary in report.failure_analysis:
            lines.append(
                f"{summary.failure_reason:28} count={summary.count}  cases={', '.join(summary.case_ids[:8])}"
                f"{'...' if len(summary.case_ids) > 8 else ''}"
            )

    if report.failure_type_analysis:
        lines.append("")
        lines.append("FAILURE TYPE ANALYSIS")
        lines.append("-" * 72)
        for summary in report.failure_type_analysis:
            lines.append(
                f"{summary.failure_type:28} count={summary.count}  "
                f"cases={', '.join(summary.case_ids[:8])}"
                f"{'...' if len(summary.case_ids) > 8 else ''}"
            )

    if report.dashboard_path:
        lines.append("")
        lines.append(f"Dashboard: {report.dashboard_path}")
    if report.artifacts_dir:
        lines.append(f"Artifacts: {report.artifacts_dir}")

    if report.worst_performing:
        lines.append("")
        lines.append("WORST PERFORMING CASES")
        lines.append("-" * 72)
        lines.append(", ".join(report.worst_performing))

    lines.append("")
    lines.append("PER-QUESTION RESULTS")
    lines.append("-" * 72)
    for result in report.question_results:
        status = "PASS" if result.answer.passed and result.retrieval.expected_chunk_found else "FAIL"
        lines.append(
            f"[{status}] {result.case_id}: rank={result.retrieval.expected_rank} "
            f"recall@1={result.retrieval.recall_at_1} answer={result.answer.passed} "
            f"citation={result.citation.passed} latency={result.total_latency_ms:.1f}ms"
        )

    lines.append("=" * 72)
    return "\n".join(lines)


def export_json_report(report: BenchmarkReport, output_path: str | Path) -> Path:
    """Write the full benchmark report to JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path


def export_csv_report(report: BenchmarkReport, output_path: str | Path) -> Path:
    """Write per-question benchmark metrics to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "case_id",
        "question",
        "document_type",
        "query_category",
        "difficulty",
        "expected_rank",
        "recall_at_1",
        "recall_at_3",
        "recall_at_5",
        "mrr_contribution",
        "precision_at_k",
        "answer_passed",
        "citation_passed",
        "context_precision",
        "hallucination_detected",
        "failure_types",
        "artifact_path",
        "retrieval_confidence",
        "retrieval_latency_ms",
        "generation_latency_ms",
        "total_latency_ms",
        "failure_reason",
        "actual_answer",
        "expected_answer",
    ]

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in report.question_results:
            writer.writerow(
                {
                    "case_id": result.case_id,
                    "question": result.question,
                    "document_type": result.document_type,
                    "query_category": result.query_category,
                    "difficulty": result.difficulty,
                    "expected_rank": result.retrieval.expected_rank,
                    "recall_at_1": result.retrieval.recall_at_1,
                    "recall_at_3": result.retrieval.recall_at_3,
                    "recall_at_5": result.retrieval.recall_at_5,
                    "mrr_contribution": result.retrieval.mrr_contribution,
                    "precision_at_k": result.retrieval.precision_at_k,
                    "answer_passed": result.answer.passed,
                    "citation_passed": result.citation.passed,
                    "context_precision": result.context_precision,
                    "hallucination_detected": result.hallucination_detected,
                    "failure_types": ",".join(f.value for f in result.failure_types),
                    "artifact_path": result.artifact_path,
                    "retrieval_confidence": result.retrieval_confidence,
                    "retrieval_latency_ms": result.retrieval_latency_ms,
                    "generation_latency_ms": result.generation_latency_ms,
                    "total_latency_ms": result.total_latency_ms,
                    "failure_reason": result.retrieval.failure_reason,
                    "actual_answer": result.answer.actual_answer,
                    "expected_answer": result.answer.expected_answer,
                }
            )
    return path


def export_summary_csv(report: BenchmarkReport, output_path: str | Path) -> Path:
    """Write aggregate benchmark metrics to CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    metrics = report.metrics
    rows = {
        "recall_at_1": metrics.recall_at_1,
        "recall_at_3": metrics.recall_at_3,
        "recall_at_5": metrics.recall_at_5,
        "mrr": metrics.mrr,
        "precision_at_k": metrics.precision_at_k,
        "citation_accuracy": metrics.citation_accuracy,
        "answer_accuracy": metrics.answer_accuracy,
        "top_1_correct_pct": metrics.top_1_correct_pct,
        "top_3_correct_pct": metrics.top_3_correct_pct,
        "avg_retrieval_confidence": metrics.avg_retrieval_confidence,
        "avg_retrieval_latency_ms": metrics.avg_retrieval_latency_ms,
        "avg_generation_latency_ms": metrics.avg_generation_latency_ms,
        "avg_total_latency_ms": metrics.avg_total_latency_ms,
        "p50_total_latency_ms": metrics.p50_total_latency_ms,
        "p95_total_latency_ms": metrics.p95_total_latency_ms,
        "context_precision": metrics.context_precision,
        "hallucination_rate": metrics.hallucination_rate,
    }

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric", "value"])
    for metric, value in rows.items():
        writer.writerow([metric, value])

    path.write_text(buffer.getvalue(), encoding="utf-8")
    return path
