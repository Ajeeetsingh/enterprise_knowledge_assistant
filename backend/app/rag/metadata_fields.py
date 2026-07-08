"""Helpers for propagating chunk metadata into retrieval results."""

from __future__ import annotations

from app.ingestion.chunker import DocumentChunk
from app.ingestion.semantic_chunking.types import ChunkMetadata


def metadata_fields_from_chunk(chunk: DocumentChunk) -> dict[str, object]:
    """Extract evaluation-relevant metadata fields from a document chunk."""
    metadata = chunk.metadata if isinstance(chunk.metadata, ChunkMetadata) else None
    page_start = metadata.page_start if metadata is not None else chunk.page_number
    page_end = metadata.page_end if metadata is not None else chunk.page_number
    return {
        "page_number": chunk.page_number or page_start,
        "page_start": page_start,
        "page_end": page_end,
        "section_title": metadata.section_title if metadata is not None else None,
        "hierarchy_path": metadata.hierarchy_path if metadata is not None else None,
        "chunk_type": metadata.chunk_type.value if metadata is not None else None,
    }
