"""Vector search candidate types."""

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.chunker import DocumentChunk


@dataclass(frozen=True)
class VectorSearchCandidate:
    """A FAISS hit before metadata rescoring."""

    chunk: DocumentChunk
    raw_cosine_score: float
    bm25_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None
    fusion_score: float | None = None
    fusion_explanation: list[str] | None = None
    source_retrievers: list[str] | None = None
