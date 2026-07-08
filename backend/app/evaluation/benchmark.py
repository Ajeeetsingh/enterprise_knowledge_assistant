"""CLI entry point for retrieval benchmark execution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.evaluation.dashboard import export_html_dashboard
from app.evaluation.dataset.loader import load_dataset, resolve_default_dataset_path
from app.evaluation.history import (
    compare_reports,
    load_best_run,
    load_previous_run,
    save_benchmark_report,
)
from app.evaluation.report import (
    export_csv_report,
    export_json_report,
    export_summary_csv,
    render_console_summary,
)
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import AnswerMatchMode, BenchmarkRunConfig


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Enterprise Knowledge Assistant retrieval benchmark.",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to the golden evaluation dataset JSON file.",
    )
    parser.add_argument(
        "--corpus",
        default=None,
        help="Path to the document corpus directory or single file.",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Directory for benchmark history and exported reports.",
    )
    parser.add_argument(
        "--role",
        default="admin",
        help="RBAC role used during benchmark execution.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Retrieval depth used for evaluation metrics.",
    )
    parser.add_argument(
        "--answer-mode",
        default=AnswerMatchMode.CONTAINS.value,
        choices=[mode.value for mode in AnswerMatchMode],
        help="Default answer evaluation mode.",
    )
    parser.add_argument(
        "--llm-provider",
        default=None,
        help="Optional LLM provider override (e.g. none, groq).",
    )
    parser.add_argument(
        "--include-document",
        action="append",
        default=None,
        help="Restrict corpus indexing to specific document filenames.",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Optional label stored in benchmark metadata.",
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="Disable regression comparison against previous/best runs.",
    )
    parser.add_argument(
        "--export-prefix",
        default=None,
        help="Optional prefix for CSV/JSON export files.",
    )
    return parser


def run_benchmark(config: BenchmarkRunConfig | None = None) -> int:
    """Execute the retrieval benchmark and print a summary."""
    if config is None:
        args = _build_parser().parse_args()
        config = BenchmarkRunConfig(
            dataset_path=args.dataset,
            corpus_path=args.corpus,
            results_dir=args.results_dir,
            role=args.role,
            retrieval_top_k=args.top_k,
            answer_match_mode=AnswerMatchMode(args.answer_mode),
            llm_provider_override=args.llm_provider,
            include_documents=args.include_document,
            run_label=args.label,
            compare_previous=not args.no_compare,
            compare_best=not args.no_compare,
        )
        export_prefix = args.export_prefix or args.label
    else:
        export_prefix = config.run_label

    dataset_path = (
        Path(config.dataset_path)
        if config.dataset_path
        else resolve_default_dataset_path()
    )
    dataset = load_dataset(dataset_path)

    runner = EvaluationRunner()
    from uuid import uuid4
    run_id = str(uuid4())
    report = runner.run_dataset(
        dataset,
        config,
        dataset_path=str(dataset_path),
        run_id=run_id,
    )

    results_dir = Path(config.results_dir) if config.results_dir else None

    prefix = export_prefix or f"benchmark_{report.run_id[:8]}"
    base_dir = Path(config.results_dir) if config.results_dir else (
        Path(__file__).resolve().parents[2] / "evaluation_results"
    )
    base_dir.mkdir(parents=True, exist_ok=True)

    dashboard_path = None
    if config.generate_dashboard:
        dashboard_path = base_dir / f"{prefix}_dashboard.html"
        export_html_dashboard(
            report,
            dashboard_path,
            results_dir=base_dir,
        )
        report.dashboard_path = str(dashboard_path)

    saved_path = save_benchmark_report(report, results_dir=results_dir)

    regression = None
    if config.compare_previous:
        previous = load_previous_run(results_dir)
        if previous is not None:
            regression = compare_reports(
                previous,
                report,
                baseline_label="Previous",
                comparison_label="Current",
            )

    print(render_console_summary(report, regression=regression))

    export_dir = saved_path.parent
    prefix = export_prefix or f"benchmark_{report.run_id[:8]}"
    json_path = export_dir / f"{prefix}.json"
    csv_path = export_dir / f"{prefix}_questions.csv"
    summary_csv_path = export_dir / f"{prefix}_summary.csv"

    export_json_report(report, json_path)
    export_csv_report(report, csv_path)
    export_summary_csv(report, summary_csv_path)

    print(f"\nSaved run: {saved_path}")
    print(f"Exported JSON: {json_path}")
    print(f"Exported CSV: {csv_path}")
    print(f"Exported summary CSV: {summary_csv_path}")
    if dashboard_path is not None:
        print(f"Exported dashboard: {dashboard_path}")
    if report.artifacts_dir:
        print(f"Artifacts directory: {report.artifacts_dir}")

    if config.compare_best:
        best = load_best_run(results_dir)
        if best is not None and best.run_id != report.run_id:
            best_comparison = compare_reports(
                best,
                report,
                baseline_label="Best",
                comparison_label="Current",
            )
            print("\nComparison against best run:")
            for delta in best_comparison.deltas:
                if "recall" in delta.metric or "accuracy" in delta.metric:
                    print(
                        f"  {delta.metric}: best={delta.before * 100:.1f}% "
                        f"current={delta.after * 100:.1f}% "
                        f"delta={(delta.delta * 100):+.1f}%"
                    )

    return 0


def main() -> None:
    """CLI main entry point."""
    raise SystemExit(run_benchmark())


if __name__ == "__main__":
    main()
