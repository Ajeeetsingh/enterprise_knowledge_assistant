"""Semantic retrieval with sentence-transformers and FAISS."""

from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.ingestion.chunker import DocumentChunk

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class RetrievalResult:
    """A single retrieval hit."""

    content: str
    source: str
    category: str
    confidence: float
    chunk_id: str


class SemanticRetriever:
    """Builds a FAISS index and performs semantic search."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model = SentenceTransformer(model_name)
        self.chunks: list[DocumentChunk] = []
        self.index: faiss.IndexFlatIP | None = None
        self._embeddings: np.ndarray | None = None

    def build_index(self, chunks: list[DocumentChunk]) -> None:
        """Embed document chunks and store them in a FAISS index."""
        if not chunks:
            raise ValueError("Cannot build index: no document chunks provided.")

        self.chunks = chunks
        texts = [chunk.content for chunk in chunks]
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        embeddings = embeddings.astype("float32")

        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        self._embeddings = embeddings

    def _encode_query(self, query: str) -> np.ndarray:
        vector = self.model.encode([query], convert_to_numpy=True, show_progress_bar=False)
        vector = vector.astype("float32")
        faiss.normalize_L2(vector)
        return vector

    def search(
        self,
        query: str,
        top_k: int = 3,
        allowed_categories: set[str] | None = None,
        category_filter: str | None = None,
        allowed_sources: set[str] | None = None,
    ) -> list[RetrievalResult]:
        """Search the FAISS index and return ranked results.

        When ``allowed_categories`` is provided, only chunks in those categories
        are returned. This enforces RBAC at retrieval time.

        When ``allowed_sources`` is provided, only chunks whose ``source``
        (filename) is in the set are returned.  This enforces document-level
        authorization introduced in Phase 5.5.  Both filters are ANDed when
        both are provided.

        Args:
            query: Natural-language search query.
            top_k: Maximum number of results to return.
            allowed_categories: Optional category whitelist (category RBAC).
            category_filter: Override ``allowed_categories`` with a single
                category (used by routing).
            allowed_sources: Optional source filename whitelist
                (document-level authorization).

        Returns:
            Ranked list of ``RetrievalResult`` objects for authorized chunks.
        """
        if self.index is None or not self.chunks:
            raise RuntimeError("Index not built. Call build_index() first.")

        permitted = allowed_categories
        if category_filter:
            permitted = {category_filter}

        query_vector = self._encode_query(query)
        search_k = min(len(self.chunks), max(top_k * 15, top_k))
        scores, indices = self.index.search(query_vector, search_k)

        results: list[RetrievalResult] = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue

            chunk = self.chunks[idx]
            if permitted and chunk.category not in permitted:
                continue

            # Document-level authorization filter (Phase 5.5).
            if allowed_sources is not None and chunk.source not in allowed_sources:
                continue

            confidence = float(max(0.0, min(1.0, score)))
            results.append(
                RetrievalResult(
                    content=chunk.content,
                    source=chunk.source,
                    category=chunk.category,
                    confidence=round(confidence, 4),
                    chunk_id=chunk.chunk_id,
                )
            )

            if len(results) >= top_k:
                break

        return results
