"""Vector store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ingestion.chunker import DocumentChunk


class VectorStore(ABC):
    """Persist and retrieve document chunk embeddings.

    Implementations store and index dense vectors:

    * ``FaissVectorStore``  — in-process FAISS index (MVP)
    * ``QdrantVectorStore`` — (future) Qdrant server
    * ``PgVectorStore``     — (future) pgvector in PostgreSQL
    * ``PineconeVectorStore`` — (future) Pinecone managed service

    The pipeline depends only on this abstraction; replacing the storage
    backend requires only a new implementation class.
    """

    @abstractmethod
    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        *,
        document_id: str | None = None,
    ) -> list[str]:
        """Index chunk embeddings and return one vector ID per chunk.

        Args:
            chunks:      Document chunks whose text was embedded.
            embeddings:  Parallel list of float vectors (one per chunk).
            document_id: Optional owning document ID for lifecycle cleanup.

        Returns:
            List of stable string identifiers for the stored vectors,
            in the same order as *chunks*.
        """

    @abstractmethod
    def remove_document(self, document_id: str) -> None:
        """Remove all vectors that belong to *document_id*.

        No-op if the document is not found.
        """

    @property
    @abstractmethod
    def size(self) -> int:
        """Return the total number of vectors currently in the store."""
