"""FAISS-backed vector store."""

from __future__ import annotations

from app.core.exceptions import VectorStoreError
from app.ingestion.chunker import DocumentChunk
from app.ingestion.vector_store.base import VectorStore


class FaissVectorStore(VectorStore):
    """In-process FAISS flat inner-product index.

    Vectors are L2-normalised before storage so cosine similarity is
    computed via inner product, matching the behaviour of
    ``SemanticRetriever`` in the existing RAG engine.

    FAISS is imported lazily on the first mutation so this class can be
    instantiated and tested without the heavy dependency installed.

    Document vectors are tracked by ``document_id`` so lifecycle delete
    can remove all chunks belonging to a document without pipeline involvement.
    """

    def __init__(self) -> None:
        self._index = None
        self._chunk_ids: list[str] = []
        self._document_ids: list[str | None] = []
        self._vectors: list[list[float]] = []
        self._dimension: int | None = None

    def _ensure_index(self, dimension: int) -> None:
        if self._index is None:
            try:
                import faiss
            except ImportError as exc:
                raise VectorStoreError(
                    "faiss-cpu is required. Install it with: pip install faiss-cpu"
                ) from exc
            self._dimension = dimension
            self._index = faiss.IndexFlatIP(dimension)
        elif dimension != self._dimension:
            raise VectorStoreError(
                f"Vector dimension mismatch: index expects {self._dimension}, "
                f"got {dimension}."
            )

    def _rebuild_index(self) -> None:
        if not self._vectors:
            self._index = None
            self._dimension = None
            return

        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise VectorStoreError(
                "faiss-cpu and numpy are required for vector indexing."
            ) from exc

        vectors = np.array(self._vectors, dtype="float32")
        faiss.normalize_L2(vectors)
        dimension = vectors.shape[1]
        self._dimension = dimension
        self._index = faiss.IndexFlatIP(dimension)
        self._index.add(vectors)

    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        *,
        document_id: str | None = None,
    ) -> list[str]:
        if not chunks:
            return []
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
                "must have the same length."
            )

        dimension = len(embeddings[0])
        if self._dimension is not None and dimension != self._dimension:
            raise VectorStoreError(
                f"Vector dimension mismatch: index expects {self._dimension}, "
                f"got {dimension}."
            )
        for embedding in embeddings:
            if len(embedding) != dimension:
                raise VectorStoreError(
                    "All embeddings in a batch must share the same dimension."
                )

        ids = [chunk.chunk_id for chunk in chunks]
        self._vectors.extend(embeddings)
        self._chunk_ids.extend(ids)
        self._document_ids.extend([document_id] * len(chunks))
        self._rebuild_index()
        return ids

    def remove_document(self, document_id: str) -> None:
        """Remove all vectors associated with *document_id*.

        No-op when the document has no indexed vectors.
        """
        if not self._vectors:
            return

        retained_vectors: list[list[float]] = []
        retained_chunk_ids: list[str] = []
        retained_document_ids: list[str | None] = []

        for vector, chunk_id, owner_id in zip(
            self._vectors,
            self._chunk_ids,
            self._document_ids,
            strict=True,
        ):
            if owner_id != document_id:
                retained_vectors.append(vector)
                retained_chunk_ids.append(chunk_id)
                retained_document_ids.append(owner_id)

        if len(retained_vectors) == len(self._vectors):
            return

        self._vectors = retained_vectors
        self._chunk_ids = retained_chunk_ids
        self._document_ids = retained_document_ids
        self._rebuild_index()

    @property
    def size(self) -> int:
        return len(self._chunk_ids)
