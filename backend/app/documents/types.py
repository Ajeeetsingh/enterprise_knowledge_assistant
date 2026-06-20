"""Ingestion pipeline context and result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.documents.metadata import DocumentMetadata

if TYPE_CHECKING:
    from app.ingestion.chunker import DocumentChunk


@dataclass
class IngestionContext:
    """Mutable state passed sequentially through pipeline stages.

    Each pipeline stage enriches this context, advancing the document from
    raw bytes through to a fully indexed, search-ready state.
    """

    filename: str
    content_type: str
    content: bytes
    document_id: str | None = None
    checksum: str | None = None
    storage_path: str | None = None
    metadata: DocumentMetadata | None = None
    tenant_id: str | None = None
    extracted_text: str | None = None
    chunks: list[DocumentChunk] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    vector_ids: list[str] = field(default_factory=list)
    chunk_count: int = 0
    embedding_count: int = 0
    indexed: bool = False
    stage_results: dict[str, str] = field(default_factory=dict)
    stage_durations: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestionResult:
    """Outcome produced after the ingestion pipeline completes."""

    metadata: DocumentMetadata
    storage_path: str | None
    chunk_count: int
    embedding_count: int
    indexed: bool

    @classmethod
    def from_context(cls, context: IngestionContext) -> IngestionResult:
        if context.metadata is None:
            raise ValueError("Ingestion context is missing document metadata.")
        return cls(
            metadata=context.metadata,
            storage_path=context.storage_path,
            chunk_count=context.chunk_count,
            embedding_count=context.embedding_count,
            indexed=context.indexed,
        )
