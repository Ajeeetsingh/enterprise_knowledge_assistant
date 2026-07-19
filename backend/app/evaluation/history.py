"""Historical benchmark result storage and regression comparison."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.evaluation.schemas import BenchmarkReport

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_DIR = BACKEND_ROOT / "evaluation_results"
BEST_RUN_FILENAME = "best_run.json"
LATEST_RUN_FILENAME = "latest_run.json"


@dataclass(frozen=True)
class MetricDelta:
    """Delta between two benchmark metric values."""

    metric: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        return self.after - self.before

    @property
    def delta_pct(self) -> float:
        if self.before == 0:
            return 0.0 if self.after == 0 else 100.0
        return (self.delta / self.before) * 100.0


@dataclass(frozen=True)
class RegressionComparison:
    """Comparison between two benchmark runs."""

    baseline_label: str
    comparison_label: str
    deltas: list[MetricDelta]


def resolve_results_dir(path: str | Path | None = None) -> Path:
    """Return the directory used to store benchmark history."""
    return Path(path) if path is not None else DEFAULT_RESULTS_DIR


def _timestamp_slug(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def save_benchmark_report(
    report: BenchmarkReport,
    *,
    results_dir: str | Path | None = None,
) -> Path:
    """Persist a benchmark report and update latest/best pointers."""
    directory = resolve_results_dir(results_dir)
    directory.mkdir(parents=True, exist_ok=True)

    run_path = directory / f"run_{_timestamp_slug(report.started_at)}_{report.run_id[:8]}.json"
    payload = report.to_dict()
    run_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    latest_path = directory / LATEST_RUN_FILENAME
    latest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    best_path = directory / BEST_RUN_FILENAME
    if best_path.exists():
        current_best = load_benchmark_report(best_path)
        if _is_better(report, current_best):
            best_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    else:
        best_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return run_path


def load_benchmark_report(path: str | Path) -> BenchmarkReport:
    """Load a serialized benchmark report."""
    from app.evaluation.report import report_from_dict

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return report_from_dict(payload)


def list_benchmark_runs(results_dir: str | Path | None = None) -> list[Path]:
    """List stored benchmark run files, newest first."""
    directory = resolve_results_dir(results_dir)
    if not directory.exists():
        return []
    return sorted(
        (
            path
            for path in directory.glob("run_*.json")
            if path.is_file()
        ),
        reverse=True,
    )


def _metric_values(report: BenchmarkReport) -> dict[str, float]:
    metrics = report.metrics
    return {
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
        "avg_total_latency_ms": metrics.avg_total_latency_ms,
        "context_precision": metrics.context_precision,
        "hallucination_rate": metrics.hallucination_rate,
    }


def _is_better(candidate: BenchmarkReport, incumbent: BenchmarkReport) -> bool:
    candidate_score = (
        candidate.metrics.recall_at_1 * 0.35
        + candidate.metrics.mrr * 0.25
        + candidate.metrics.answer_accuracy * 0.25
        + candidate.metrics.citation_accuracy * 0.15
    )
    incumbent_score = (
        incumbent.metrics.recall_at_1 * 0.35
        + incumbent.metrics.mrr * 0.25
        + incumbent.metrics.answer_accuracy * 0.25
        + incumbent.metrics.citation_accuracy * 0.15
    )
    return candidate_score > incumbent_score


def compare_reports(
    baseline: BenchmarkReport,
    comparison: BenchmarkReport,
    *,
    baseline_label: str = "Before",
    comparison_label: str = "After",
) -> RegressionComparison:
    """Compare aggregate metrics between two benchmark runs."""
    baseline_metrics = _metric_values(baseline)
    comparison_metrics = _metric_values(comparison)

    deltas = [
        MetricDelta(
            metric=metric,
            before=baseline_metrics[metric],
            after=comparison_metrics[metric],
        )
        for metric in baseline_metrics
    ]
    return RegressionComparison(
        baseline_label=baseline_label,
        comparison_label=comparison_label,
        deltas=deltas,
    )


def load_previous_run(results_dir: str | Path | None = None) -> BenchmarkReport | None:
    """Load the most recent stored benchmark run before the latest pointer."""
    directory = resolve_results_dir(results_dir)
    runs = list_benchmark_runs(directory)
    if len(runs) < 2:
        return None
    return load_benchmark_report(runs[1])


def load_best_run(results_dir: str | Path | None = None) -> BenchmarkReport | None:
    """Load the best recorded benchmark run."""
    directory = resolve_results_dir(results_dir)
    best_path = directory / BEST_RUN_FILENAME
    if not best_path.exists():
        return None
    return load_benchmark_report(best_path)
