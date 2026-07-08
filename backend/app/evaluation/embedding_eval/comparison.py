"""Comparison tables, rankings, and model recommendations."""

from __future__ import annotations

from datetime import datetime

from app.evaluation.embedding_eval.schemas import (
    EmbeddingAwards,
    EmbeddingComparisonReport,
    EmbeddingModelMetrics,
)


def _rank_by(
    metrics: list[EmbeddingModelMetrics],
    *,
    key,
    reverse: bool = True,
) -> dict[str, int]:
    ordered = sorted(metrics, key=key, reverse=reverse)
    return {item.model_id: rank for rank, item in enumerate(ordered, start=1)}


def assign_ranks(metrics: list[EmbeddingModelMetrics]) -> list[EmbeddingModelMetrics]:
    """Assign recall, latency, accuracy, and tradeoff ranks to each model."""
    recall_ranks = _rank_by(metrics, key=lambda item: (item.recall_at_5, item.mrr))
    latency_ranks = _rank_by(
        metrics,
        key=lambda item: item.avg_query_latency_ms,
        reverse=False,
    )
    accuracy_ranks = _rank_by(
        metrics,
        key=lambda item: (
            item.answer_accuracy,
            item.citation_accuracy,
            item.context_precision,
        ),
    )
    tradeoff_ranks = _rank_by(
        metrics,
        key=lambda item: (
            item.recall_at_5,
            -item.avg_query_latency_ms,
            item.mrr,
        ),
    )

    ranked: list[EmbeddingModelMetrics] = []
    for item in metrics:
        tradeoff_score = (
            item.recall_at_5 * 0.55
            + item.mrr * 0.25
            + item.answer_accuracy * 0.20
            - (item.avg_query_latency_ms / 1000.0) * 0.05
        )
        overall_candidates = [
            recall_ranks[item.model_id],
            accuracy_ranks[item.model_id],
            tradeoff_ranks[item.model_id],
        ]
        ranked.append(
            EmbeddingModelMetrics(
                **{
                    **item.__dict__,
                    "rank_recall": recall_ranks[item.model_id],
                    "rank_latency": latency_ranks[item.model_id],
                    "rank_accuracy": accuracy_ranks[item.model_id],
                    "rank_tradeoff": tradeoff_ranks[item.model_id],
                    "overall_rank": min(overall_candidates),
                }
            )
        )

    ranked.sort(
        key=lambda item: (
            item.rank_tradeoff or 999,
            item.rank_recall or 999,
            item.avg_query_latency_ms,
        )
    )
    return ranked


def build_awards(metrics: list[EmbeddingModelMetrics]) -> EmbeddingAwards:
    """Select best models across key dimensions."""
    by_recall = min(metrics, key=lambda item: item.rank_recall or 999)
    by_latency = min(metrics, key=lambda item: item.rank_latency or 999)
    by_accuracy = min(metrics, key=lambda item: item.rank_accuracy or 999)
    by_tradeoff = min(metrics, key=lambda item: item.rank_tradeoff or 999)
    return EmbeddingAwards(
        best_recall=by_recall.model_id,
        fastest=by_latency.model_id,
        best_accuracy=by_accuracy.model_id,
        best_tradeoff=by_tradeoff.model_id,
    )


def recommend_model(
    metrics: list[EmbeddingModelMetrics],
) -> tuple[str, str]:
    """Recommend a production model based on weighted benchmark performance."""
    if not metrics:
        return "", "No models evaluated."

    scored = []
    for item in metrics:
        score = (
            item.recall_at_5 * 0.30
            + item.recall_at_1 * 0.15
            + item.mrr * 0.20
            + item.answer_accuracy * 0.15
            + item.context_precision * 0.10
            + item.citation_accuracy * 0.10
            - (item.avg_query_latency_ms / 100.0) * 0.02
        )
        scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    best_score, best = scored[0]
    baseline = next((item for item in metrics if "minilm" in item.model_id), metrics[0])
    delta_recall = (best.recall_at_5 - baseline.recall_at_5) * 100
    reason = (
        f"{best.model_label} ({best.model_id}) achieves the best weighted benchmark "
        f"score ({best_score:.3f}) with Recall@5={best.recall_at_5 * 100:.1f}% "
        f"and MRR={best.mrr:.3f}. "
        f"Compared to baseline, Recall@5 delta is {delta_recall:+.1f} percentage points."
    )
    return best.model_id, reason


def render_comparison_table(metrics: list[EmbeddingModelMetrics]) -> str:
    """Render a markdown comparison table for evaluated models."""
    headers = [
        "Model",
        "Recall@1",
        "Recall@5",
        "MRR",
        "Answer Acc.",
        "Latency (ms)",
        "Dimension",
        "Memory (MB)",
        "Ranking",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for item in metrics:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"{item.model_label} (`{item.model_id}`)",
                    f"{item.recall_at_1 * 100:.1f}%",
                    f"{item.recall_at_5 * 100:.1f}%",
                    f"{item.mrr:.3f}",
                    f"{item.answer_accuracy * 100:.1f}%",
                    f"{item.avg_query_latency_ms:.1f}",
                    str(item.dimension),
                    f"{item.memory_usage_mb:.0f}",
                    str(item.rank_tradeoff or "-"),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def build_comparison_report(
    *,
    started_at: datetime,
    completed_at: datetime,
    dataset_path: str,
    corpus_path: str,
    case_count: int,
    model_metrics: list[EmbeddingModelMetrics],
    metadata: dict | None = None,
) -> EmbeddingComparisonReport:
    """Build the full comparison report with ranks, awards, and recommendation."""
    ranked = assign_ranks(model_metrics)
    awards = build_awards(ranked)
    recommended_id, reason = recommend_model(ranked)
    return EmbeddingComparisonReport(
        started_at=started_at,
        completed_at=completed_at,
        dataset_path=dataset_path,
        corpus_path=corpus_path,
        case_count=case_count,
        model_metrics=ranked,
        awards=awards,
        recommended_model_id=recommended_id,
        recommendation_reason=reason,
        metadata=metadata or {},
    )
