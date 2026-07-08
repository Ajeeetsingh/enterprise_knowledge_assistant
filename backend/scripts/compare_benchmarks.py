"""Unified benchmark comparison utility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = BACKEND_ROOT / "evaluation_results"

METRICS = [
    "recall_at_1",
    "recall_at_3",
    "recall_at_5",
    "mrr",
    "answer_accuracy",
    "citation_accuracy",
    "context_precision",
    "hallucination_rate",
    "avg_retrieval_latency_ms",
    "avg_total_latency_ms",
]


def _load_report(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _metric(report: dict, name: str) -> float:
    return float(report.get("metrics", {}).get(name, 0.0))


def _case_map(report: dict) -> dict[str, dict]:
    return {item["case_id"]: item for item in report.get("question_results", [])}


def _rank(report: dict, case_id: str) -> int | None:
    case = _case_map(report).get(case_id)
    if case is None:
        return None
    return case.get("retrieval", {}).get("expected_rank")


def _movement(baseline: dict, current: dict) -> dict[str, list[str]]:
    improved: list[str] = []
    unchanged: list[str] = []
    degraded: list[str] = []

    for case_id, after in _case_map(current).items():
        before = _case_map(baseline).get(case_id)
        if before is None:
            continue
        before_rank = before.get("retrieval", {}).get("expected_rank")
        after_rank = after.get("retrieval", {}).get("expected_rank")
        before_found = before.get("retrieval", {}).get("semantic_match_found")
        after_found = after.get("retrieval", {}).get("semantic_match_found")

        if before_rank == after_rank and before_found == after_found:
            unchanged.append(case_id)
        elif (
            (before_rank is None and after_rank is not None)
            or (before_rank is not None and after_rank is not None and after_rank < before_rank)
            or (not before_found and after_found)
        ):
            improved.append(case_id)
        elif (
            (before_rank is not None and after_rank is None)
            or (before_rank is not None and after_rank is not None and after_rank > before_rank)
            or (before_found and not after_found)
        ):
            degraded.append(case_id)
        else:
            unchanged.append(case_id)

    return {"improved": improved, "unchanged": unchanged, "degraded": degraded}


def _hybrid_contributions(report: dict) -> dict[str, int]:
    dense_only = sparse_only = both = 0
    for result in report.get("question_results", []):
        details = result.get("retrieval", {}).get("top_k_details", [])
        if not details:
            continue
        sources = details[0].get("source_retrievers") or []
        if "dense" in sources and "sparse" in sources:
            both += 1
        elif "sparse" in sources:
            sparse_only += 1
        elif "dense" in sources:
            dense_only += 1
    return {"dense_only": dense_only, "sparse_only": sparse_only, "both": both}


def _print_comparison(baseline: dict, current: dict, *, title: str) -> None:
    print(title)
    print("=" * 72)
    print(f"Baseline: {baseline.get('metadata', {}).get('run_label', baseline.get('run_id', 'n/a'))}")
    print(f"Current:  {current.get('metadata', {}).get('run_label', current.get('run_id', 'n/a'))}")
    metadata = current.get("metadata", {})
    for key in (
        "hybrid_enabled",
        "reranking_enabled",
        "query_intelligence_enabled",
        "rerank_model",
    ):
        if key in metadata:
            print(f"  {key}: {metadata[key]}")
    print()

    for metric in METRICS:
        before = _metric(baseline, metric)
        after = _metric(current, metric)
        if "latency" in metric:
            delta = after - before
            print(f"{metric:28s} {before:8.3f} -> {after:8.3f} ({delta:+.3f} ms)")
        else:
            delta = (after - before) * 100
            print(f"{metric:28s} {before * 100:6.1f}% -> {after * 100:6.1f}% ({delta:+.1f} pp)")

    movement = _movement(baseline, current)
    print("\nQuestion Movement")
    print(f"  Improved:  {len(movement['improved'])}")
    print(f"  Unchanged: {len(movement['unchanged'])}")
    print(f"  Degraded:  {len(movement['degraded'])}")

    if movement["improved"]:
        print("\nSample improved cases:")
        for case_id in movement["improved"][:10]:
            print(f"  {case_id}: rank {_rank(baseline, case_id)} -> {_rank(current, case_id)}")

    if movement["degraded"]:
        print("\nSample degraded cases:")
        for case_id in movement["degraded"][:10]:
            print(f"  {case_id}: rank {_rank(baseline, case_id)} -> {_rank(current, case_id)}")

    contributions = _hybrid_contributions(current)
    if any(contributions.values()):
        print("\nTop-1 Retriever Contributions (current)")
        print(f"  Dense only:  {contributions['dense_only']}")
        print(f"  Sparse only: {contributions['sparse_only']}")
        print(f"  Both:        {contributions['both']}")

    failures = current.get("failure_type_analysis", [])
    if failures:
        print("\nFailure Type Distribution (current)")
        for item in failures:
            print(f"  {item.get('failure_type')}: {item.get('count', 0)}")
    print()


def _compare_pair(baseline_path: Path, current_path: Path) -> int:
    if not baseline_path.exists():
        print(f"Baseline not found: {baseline_path}")
        return 1
    if not current_path.exists():
        print(f"Current not found: {current_path}")
        return 1
    _print_comparison(
        _load_report(baseline_path),
        _load_report(current_path),
        title=f"Benchmark Comparison: {baseline_path.name} -> {current_path.name}",
    )
    return 0


def _compare_all(results_dir: Path) -> int:
    runs = sorted(results_dir.glob("run_*.json"))
    if len(runs) < 2:
        print("Need at least two run_*.json files for --all comparison.")
        return 1
    baseline = _load_report(runs[-2])
    current = _load_report(runs[-1])
    _print_comparison(
        baseline,
        current,
        title=f"Sequential Comparison: {runs[-2].name} -> {runs[-1].name}",
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare benchmark JSON reports.")
    parser.add_argument("--baseline", type=Path, help="Baseline benchmark JSON")
    parser.add_argument("--current", type=Path, help="Current benchmark JSON")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Compare latest_run.json vs best_run.json in results dir.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Compare the two most recent run_*.json files.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help="Evaluation results directory.",
    )
    args = parser.parse_args(argv)

    if args.latest:
        return _compare_pair(
            args.results_dir / "best_run.json",
            args.results_dir / "latest_run.json",
        )
    if args.all:
        return _compare_all(args.results_dir)
    if args.baseline and args.current:
        return _compare_pair(args.baseline, args.current)

    parser.error("Provide --baseline and --current, or use --latest / --all")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
