"""FAISS-backed vector store with semantic search."""

from __future__ import annotations

import logging

from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger, log_with_fields
from app.embeddings.manager import EmbeddingModelManager, get_embedding_manager
from app.ingestion.chunker import DocumentChunk
from app.ingestion.vector_store.base import VectorStore
from app.ingestion.vector_store.candidates import VectorSearchCandidate
from app.rag.types import EMBEDDING_MODEL_NAME, RetrievalResult

logger = get_logger(__name__)


class FaissVectorStore(VectorStore):
    """In-process FAISS flat inner-product index with chunk metadata.

    Vectors are L2-normalised before storage so cosine similarity is
    computed via inner product, matching ``SemanticRetriever``.

    Chunk text and metadata are stored alongside vectors so the same index
    used during document ingestion powers chat retrieval.
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        embedding_manager: EmbeddingModelManager | None = None,
    ) -> None:
        self._model_name = model_name
        self._embedding_manager = embedding_manager or get_embedding_manager()
        self._index = None
        self._chunks: list[DocumentChunk] = []
        self._chunk_ids: list[str] = []
        self._document_ids: list[str | None] = []
        self._vectors: list[list[float]] = []
        self._dimension: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int | None:
        return self._dimension

    @property
    def chunks(self) -> list[DocumentChunk]:
        """Return a snapshot of indexed chunks (for diagnostics and tests)."""
        return list(self._chunks)

    def _load_model(self):
        return self._embedding_manager.get_model()

    def _encode_query(self, query: str):
        try:
            import numpy as np
            import faiss
        except ImportError as exc:
            raise VectorStoreError(
                "faiss-cpu and numpy are required for semantic search."
            ) from exc

        model = self._load_model()
        vector = model.encode([query], convert_to_numpy=True, show_progress_bar=False)
        vector = vector.astype("float32")
        faiss.normalize_L2(vector)
        return vector

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

    def clear(self) -> None:
        """Remove all vectors and chunk metadata from the store."""
        self._index = None
        self._chunks.clear()
        self._chunk_ids.clear()
        self._document_ids.clear()
        self._vectors.clear()
        self._dimension = None

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
        self._chunks.extend(chunks)
        self._chunk_ids.extend(ids)
        self._document_ids.extend([document_id] * len(chunks))
        self._rebuild_index()

        avg_chunk_size = round(
            sum(len(chunk.content) for chunk in chunks) / len(chunks),
        )
        log_with_fields(
            logger,
            logging.INFO,
            "Vector store updated",
            collection="faiss_in_process",
            document_id=document_id,
            vectors_added=len(chunks),
            total_vectors=self.size,
            embedding_dimension=dimension,
            embedding_model=self._model_name,
            avg_chunk_size=avg_chunk_size,
            chunk_ids=ids[:5],
        )
        return ids

    def remove_document(self, document_id: str) -> None:
        """Remove all vectors associated with *document_id*."""
        if not self._vectors:
            return

        retained_vectors: list[list[float]] = []
        retained_chunks: list[DocumentChunk] = []
        retained_chunk_ids: list[str] = []
        retained_document_ids: list[str | None] = []

        for vector, chunk, chunk_id, owner_id in zip(
            self._vectors,
            self._chunks,
            self._chunk_ids,
            self._document_ids,
            strict=True,
        ):
            if owner_id != document_id:
                retained_vectors.append(vector)
                retained_chunks.append(chunk)
                retained_chunk_ids.append(chunk_id)
                retained_document_ids.append(owner_id)

        if len(retained_vectors) == len(self._vectors):
            return

        removed = len(self._vectors) - len(retained_vectors)
        self._vectors = retained_vectors
        self._chunks = retained_chunks
        self._chunk_ids = retained_chunk_ids
        self._document_ids = retained_document_ids
        self._rebuild_index()

        log_with_fields(
            logger,
            logging.INFO,
            "Vector store document removed",
            collection="faiss_in_process",
            document_id=document_id,
            vectors_removed=removed,
            total_vectors=self.size,
        )

    def gather_candidates(
        self,
        query: str,
        *,
        limit: int,
        allowed_categories: set[str] | None = None,
        category_filter: str | None = None,
        allowed_sources: set[str] | None = None,
        min_score: float = 0.0,
    ) -> list[VectorSearchCandidate]:
        """Return authorized FAISS hits for metadata rescoring."""
        if self._index is None or not self._chunks:
            return []

        permitted = allowed_categories
        if category_filter:
            permitted = {category_filter}

        query_vector = self._encode_query(query)
        search_k = min(len(self._chunks), max(limit, 1))
        scores, indices = self._index.search(query_vector, search_k)

        candidates: list[VectorSearchCandidate] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx < 0:
                continue

            chunk = self._chunks[idx]
            if permitted and chunk.category not in permitted:
                continue
            if allowed_sources is not None and chunk.source not in allowed_sources:
                continue

            raw_confidence = float(max(0.0, min(1.0, score)))
            if raw_confidence < min_score:
                continue

            candidates.append(
                VectorSearchCandidate(
                    chunk=chunk,
                    raw_cosine_score=raw_confidence,
                )
            )
            if len(candidates) >= limit:
                break
        return candidates

    def search(
        self,
        query: str,
        top_k: int = 3,
        allowed_categories: set[str] | None = None,
        category_filter: str | None = None,
        allowed_sources: set[str] | None = None,
        *,
        min_score: float = 0.0,
    ) -> list[RetrievalResult]:
        """Search indexed chunks and return ranked retrieval hits."""
        if self._index is None or not self._chunks:
            log_with_fields(
                logger,
                logging.WARNING,
                "Vector store search skipped",
                reason="empty_index",
                query=query,
            )
            return []

        permitted = allowed_categories
        if category_filter:
            permitted = {category_filter}

        query_vector = self._encode_query(query)
        search_k = min(len(self._chunks), max(top_k * 15, top_k))
        scores, indices = self._index.search(query_vector, search_k)

        results: list[RetrievalResult] = []
        for score, idx in zip(scores[0], indices[0], strict=True):
            if idx < 0:
                continue

            chunk = self._chunks[idx]
            if permitted and chunk.category not in permitted:
                continue
            if allowed_sources is not None and chunk.source not in allowed_sources:
                continue

            from app.rag.metadata_fields import metadata_fields_from_chunk
            from app.rag.types import calibrate_confidence
            raw_confidence = float(max(0.0, min(1.0, score)))
            calibrated = calibrate_confidence(raw_confidence)
            if raw_confidence < min_score:
                continue

            results.append(
                RetrievalResult(
                    content=chunk.content,
                    source=chunk.source,
                    category=chunk.category,
                    confidence=calibrated,
                    chunk_id=chunk.chunk_id,
                    **metadata_fields_from_chunk(chunk),
                )
            )
            if len(results) >= top_k:
                break

        log_with_fields(
            logger,
            logging.INFO,
            "Vector store search completed",
            collection="faiss_in_process",
            query=query,
            embedding_generated=True,
            embedding_dimension=self._dimension,
            top_k_requested=top_k,
            candidates_scanned=int(search_k),
            documents_returned=len({result.source for result in results}),
            chunks_returned=len(results),
            similarity_scores=[result.confidence for result in results],
            min_score_threshold=min_score,
            chunk_ids=[result.chunk_id for result in results],
            document_ids=[result.source for result in results],
            allowed_categories=sorted(permitted) if permitted else None,
            allowed_sources_count=len(allowed_sources) if allowed_sources else None,
        )
        return results

    @property
    def size(self) -> int:
        return len(self._chunk_ids)

    @property
    def index_size_bytes(self) -> int:
        """Approximate in-memory FAISS index size for evaluation reporting."""
        if not self._vectors:
            return 0
        dimension = self._dimension or len(self._vectors[0])
        return len(self._vectors) * dimension * 4
