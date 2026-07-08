"""Infrastructure metrics for embedding evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from app.evaluation.bootstrap import BootstrapResult
from app.evaluation.embedding_eval.schemas import EmbeddingModelMetrics
from app.evaluation.schemas import BenchmarkReport
from app.embeddings.registry import EmbeddingModelSpec


def _memory_usage_mb() -> float:
    try:
        import psutil

        process = psutil.Process()
        return round(process.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return 0.0


def build_model_metrics(
    *,
    spec: EmbeddingModelSpec,
    bootstrap: BootstrapResult,
    report: BenchmarkReport,
    memory_usage_mb: float | None = None,
) -> EmbeddingModelMetrics:
    """Combine bootstrap and benchmark metrics for one embedding model."""
    metrics = report.metrics
    return EmbeddingModelMetrics(
        model_id=spec.id,
        model_label=spec.label,
        model_name=spec.model_name,
        dimension=bootstrap.embedding_dimension,
        recall_at_1=metrics.recall_at_1,
        recall_at_3=metrics.recall_at_3,
        recall_at_5=metrics.recall_at_5,
        mrr=metrics.mrr,
        answer_accuracy=metrics.answer_accuracy,
        citation_accuracy=metrics.citation_accuracy,
        context_precision=metrics.context_precision,
        hallucination_rate=metrics.hallucination_rate,
        avg_retrieval_confidence=metrics.avg_retrieval_confidence,
        model_load_ms=bootstrap.model_load_ms,
        embedding_time_ms=bootstrap.embedding_time_ms,
        index_build_ms=bootstrap.index_build_ms,
        avg_query_latency_ms=metrics.avg_retrieval_latency_ms,
        memory_usage_mb=memory_usage_mb if memory_usage_mb is not None else _memory_usage_mb(),
        index_size_bytes=bootstrap.index_size_bytes,
        total_chunks=bootstrap.total_chunks,
        benchmark_run_id=report.run_id,
    )


def export_metrics_json(
    metrics: list[EmbeddingModelMetrics],
    path: str | Path,
) -> Path:
    """Persist per-model metrics as JSON."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "model_id": item.model_id,
            "model_label": item.model_label,
            "model_name": item.model_name,
            "dimension": item.dimension,
            "recall_at_1": item.recall_at_1,
            "recall_at_3": item.recall_at_3,
            "recall_at_5": item.recall_at_5,
            "mrr": item.mrr,
            "answer_accuracy": item.answer_accuracy,
            "citation_accuracy": item.citation_accuracy,
            "context_precision": item.context_precision,
            "hallucination_rate": item.hallucination_rate,
            "avg_retrieval_confidence": item.avg_retrieval_confidence,
            "model_load_ms": item.model_load_ms,
            "embedding_time_ms": item.embedding_time_ms,
            "index_build_ms": item.index_build_ms,
            "avg_query_latency_ms": item.avg_query_latency_ms,
            "memory_usage_mb": item.memory_usage_mb,
            "index_size_bytes": item.index_size_bytes,
            "total_chunks": item.total_chunks,
            "benchmark_run_id": item.benchmark_run_id,
        }
        for item in metrics
    ]
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output
