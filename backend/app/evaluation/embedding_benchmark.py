"""CLI entry point for multi-model embedding evaluation."""

from __future__ import annotations

import argparse

from app.evaluation.embedding_eval import EmbeddingEvaluationConfig, EmbeddingEvaluationFramework
from app.evaluation.embedding_eval.comparison import render_comparison_table


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate multiple embedding models against the golden benchmark.",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to the golden evaluation dataset JSON file.",
    )
    parser.add_argument(
        "--corpus",
        default=None,
        help="Path to the document corpus directory.",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Directory for comparison reports and per-model artifacts.",
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="Path to the embedding model registry JSON file.",
    )
    parser.add_argument(
        "--model",
        action="append",
        default=None,
        dest="models",
        help="Evaluate only the given model id (repeatable). Defaults to all registry models.",
    )
    parser.add_argument(
        "--label",
        default="embedding_comparison",
        help="Output filename prefix for comparison artifacts.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Retrieval depth used during benchmark evaluation.",
    )
    parser.add_argument(
        "--llm-provider",
        default="none",
        help="LLM provider override for answer evaluation.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable bootstrap metadata caching.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    config = EmbeddingEvaluationConfig(
        dataset_path=args.dataset,
        corpus_path=args.corpus,
        results_dir=args.results_dir,
        registry_path=args.registry,
        model_ids=args.models,
        retrieval_top_k=args.top_k,
        llm_provider_override=args.llm_provider,
        run_label=args.label,
        use_cache=not args.no_cache,
    )

    report = EmbeddingEvaluationFramework().run(config)

    print("\nEmbedding Model Comparison")
    print("=" * 72)
    print(render_comparison_table(report.model_metrics))
    print("Awards")
    print(f"  Best Recall:    {report.awards.best_recall}")
    print(f"  Fastest:        {report.awards.fastest}")
    print(f"  Best Accuracy:  {report.awards.best_accuracy}")
    print(f"  Best Tradeoff:  {report.awards.best_tradeoff}")
    print("\nRecommendation")
    print(f"  Model: {report.recommended_model_id}")
    print(f"  Reason: {report.recommendation_reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
