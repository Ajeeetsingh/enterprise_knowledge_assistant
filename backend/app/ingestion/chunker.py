"""Text chunking for document ingestion."""

from __future__ import annotations

from dataclasses import dataclass

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50


@dataclass
class DocumentChunk:
    """A searchable chunk derived from a source document."""

    chunk_id: str
    content: str
    source: str
    category: str
    chunk_index: int


def chunk_text(text: str, source: str, category: str) -> list[DocumentChunk]:
    """Split text into overlapping chunks for embedding."""
    text = " ".join(text.split())
    if not text:
        return []

    chunks: list[DocumentChunk] = []
    start = 0
    index = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{source}::{index}",
                    content=chunk_content,
                    source=source,
                    category=category,
                    chunk_index=index,
                )
            )
            index += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks
