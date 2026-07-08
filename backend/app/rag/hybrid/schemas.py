"""Hybrid retrieval data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ingestion.chunker import DocumentChunk


@dataclass(frozen=True)
class SparseSearchHit:
    """A BM25 retrieval hit before fusion."""

    chunk: DocumentChunk
    bm25_score: float
    rank: int


@dataclass(frozen=True)
class DenseSearchHit:
    """A dense retrieval hit before fusion."""

    chunk: DocumentChunk
    raw_cosine_score: float
    rank: int


@dataclass(frozen=True)
class FusedCandidate:
    """Candidate after reciprocal rank fusion."""

    chunk: DocumentChunk
    fusion_score: float
    dense_rank: int | None
    sparse_rank: int | None
    raw_cosine_score: float
    bm25_score: float | None
    source_retrievers: tuple[str, ...]
    fusion_explanation: tuple[str, ...] = ()


@dataclass
class HybridRetrievalMetrics:
    """Latency and candidate statistics for one hybrid query."""

    dense_latency_ms: float = 0.0
    sparse_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    metadata_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    dense_candidate_count: int = 0
    sparse_candidate_count: int = 0
    fused_candidate_count: int = 0
    dense_only_count: int = 0
    sparse_only_count: int = 0
    both_count: int = 0
    fusion_statistics: dict[str, float] = field(default_factory=dict)
