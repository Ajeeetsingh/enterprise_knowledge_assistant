"""Unit tests for embedding comparison reporting."""

from __future__ import annotations

from app.evaluation.embedding_eval.comparison import (
    assign_ranks,
    build_awards,
    recommend_model,
    render_comparison_table,
)
from app.evaluation.embedding_eval.schemas import EmbeddingModelMetrics


def _metric(
    model_id: str,
    *,
    recall_at_5: float,
    recall_at_1: float = 0.1,
    mrr: float = 0.2,
    latency: float = 20.0,
    answer_accuracy: float = 0.2,
    citation_accuracy: float = 0.2,
    context_precision: float = 0.2,
) -> EmbeddingModelMetrics:
    return EmbeddingModelMetrics(
        model_id=model_id,
        model_label=model_id,
        model_name=f"models/{model_id}",
        dimension=384,
        recall_at_1=recall_at_1,
        recall_at_3=recall_at_5 - 0.05,
        recall_at_5=recall_at_5,
        mrr=mrr,
        answer_accuracy=answer_accuracy,
        citation_accuracy=citation_accuracy,
        context_precision=context_precision,
        hallucination_rate=0.1,
        avg_retrieval_confidence=0.5,
        model_load_ms=100.0,
        embedding_time_ms=1000.0,
        index_build_ms=1200.0,
        avg_query_latency_ms=latency,
        memory_usage_mb=256.0,
        index_size_bytes=1024,
        total_chunks=100,
    )


def test_assign_ranks_orders_by_recall_and_latency() -> None:
    ranked = assign_ranks(
        [
            _metric("slow", recall_at_5=0.6, latency=40.0),
            _metric("fast", recall_at_5=0.5, latency=10.0),
        ]
    )
    by_id = {item.model_id: item for item in ranked}
    assert by_id["slow"].rank_recall == 1
    assert by_id["fast"].rank_latency == 1


def test_build_awards_selects_best_models() -> None:
    metrics = assign_ranks(
        [
            _metric("baseline", recall_at_5=0.4, latency=15.0),
            _metric("winner", recall_at_5=0.6, latency=12.0, answer_accuracy=0.5),
        ]
    )
    awards = build_awards(metrics)
    assert awards.best_recall == "winner"


def test_recommend_model_prefers_higher_weighted_score() -> None:
    metrics = assign_ranks(
        [
            _metric("minilm-l6-v2", recall_at_5=0.4, recall_at_1=0.2, mrr=0.3),
            _metric("bge-base-en-v1.5", recall_at_5=0.55, recall_at_1=0.35, mrr=0.42),
        ]
    )
    recommended_id, reason = recommend_model(metrics)
    assert recommended_id == "bge-base-en-v1.5"
    assert "outperforms" in reason or "best" in reason


def test_render_comparison_table_includes_models() -> None:
    metrics = assign_ranks([_metric("baseline", recall_at_5=0.4)])
    table = render_comparison_table(metrics)
    assert "baseline" in table
    assert "Recall@1" in table
