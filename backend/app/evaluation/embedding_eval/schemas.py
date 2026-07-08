"""Schemas for multi-model embedding evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class EmbeddingEvaluationConfig:
    """Configuration for a multi-model embedding evaluation run."""

    dataset_path: str | None = None
    corpus_path: str | None = None
    results_dir: str | None = None
    registry_path: str | None = None
    model_ids: list[str] | None = None
    role: str = "admin"
    retrieval_top_k: int = 5
    llm_provider_override: str | None = "none"
    include_documents: list[str] | None = None
    run_label: str | None = None
    use_cache: bool = True


@dataclass
class EmbeddingModelMetrics:
    """Benchmark and infrastructure metrics for one embedding model."""

    model_id: str
    model_label: str
    model_name: str
    dimension: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float
    answer_accuracy: float
    citation_accuracy: float
    context_precision: float
    hallucination_rate: float
    avg_retrieval_confidence: float
    model_load_ms: float
    embedding_time_ms: float
    index_build_ms: float
    avg_query_latency_ms: float
    memory_usage_mb: float
    index_size_bytes: int
    total_chunks: int
    benchmark_run_id: str | None = None
    rank_recall: int | None = None
    rank_latency: int | None = None
    rank_accuracy: int | None = None
    rank_tradeoff: int | None = None
    overall_rank: int | None = None


@dataclass(frozen=True)
class EmbeddingAwards:
    """Best-model awards across the evaluated cohort."""

    best_recall: str
    fastest: str
    best_accuracy: str
    best_tradeoff: str


@dataclass
class EmbeddingComparisonReport:
    """Full multi-model embedding comparison report."""

    started_at: datetime
    completed_at: datetime
    dataset_path: str
    corpus_path: str
    case_count: int
    model_metrics: list[EmbeddingModelMetrics]
    awards: EmbeddingAwards
    recommended_model_id: str
    recommendation_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "dataset_path": self.dataset_path,
            "corpus_path": self.corpus_path,
            "case_count": self.case_count,
            "model_metrics": [
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
                    "rank_recall": item.rank_recall,
                    "rank_latency": item.rank_latency,
                    "rank_accuracy": item.rank_accuracy,
                    "rank_tradeoff": item.rank_tradeoff,
                    "overall_rank": item.overall_rank,
                }
                for item in self.model_metrics
            ],
            "awards": {
                "best_recall": self.awards.best_recall,
                "fastest": self.awards.fastest,
                "best_accuracy": self.awards.best_accuracy,
                "best_tradeoff": self.awards.best_tradeoff,
            },
            "recommended_model_id": self.recommended_model_id,
            "recommendation_reason": self.recommendation_reason,
            "metadata": self.metadata,
        }
