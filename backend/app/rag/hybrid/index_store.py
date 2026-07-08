"""Hybrid index store keeping FAISS and BM25 synchronized."""

from __future__ import annotations

from app.ingestion.chunker import DocumentChunk
from app.ingestion.vector_store.base import VectorStore
from app.ingestion.vector_store.faiss_store import FaissVectorStore
from app.rag.hybrid.bm25 import BM25Index


class HybridIndexStore(VectorStore):
    """Vector store wrapper that maintains synchronized dense and sparse indexes."""

    def __init__(
        self,
        faiss_store: FaissVectorStore,
        bm25_index: BM25Index,
    ) -> None:
        self._faiss = faiss_store
        self._bm25 = bm25_index

    @property
    def faiss_store(self) -> FaissVectorStore:
        return self._faiss

    @property
    def bm25_index(self) -> BM25Index:
        return self._bm25

    @property
    def model_name(self) -> str:
        return self._faiss.model_name

    @property
    def dimension(self) -> int | None:
        return self._faiss.dimension

    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        *,
        document_id: str | None = None,
    ) -> list[str]:
        ids = self._faiss.add_chunks(chunks, embeddings, document_id=document_id)
        self._bm25.add_chunks(chunks, document_id=document_id)
        return ids

    def remove_document(self, document_id: str) -> None:
        self._faiss.remove_document(document_id)
        self._bm25.remove_document(document_id)

    def clear(self) -> None:
        self._faiss.clear()
        self._bm25.clear()

    @property
    def size(self) -> int:
        return self._faiss.size

    def gather_candidates(self, *args, **kwargs):
        return self._faiss.gather_candidates(*args, **kwargs)

    def search(self, *args, **kwargs):
        return self._faiss.search(*args, **kwargs)
