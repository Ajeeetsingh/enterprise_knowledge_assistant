"""Reranking data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RerankerMetrics:
    """Telemetry for one reranking invocation."""

    model_id: str
    model_name: str
    candidates_reranked: int
    batch_size: int
    inference_latency_ms: float
    average_score: float
    top_score: float
    device: str
    fallback_used: bool = False
    fallback_reason: str | None = None


@dataclass
class RerankOutcome:
    """Result of a reranking pass."""

    scores: list[float]
    metrics: RerankerMetrics
    fallback_used: bool = False
