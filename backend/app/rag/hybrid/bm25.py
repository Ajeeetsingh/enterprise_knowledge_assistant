"""BM25 sparse index with persistence and incremental updates."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from app.core.logging import get_logger, log_with_fields
from app.ingestion.chunker import DocumentChunk
from app.ingestion.retrieval_text import build_retrieval_text, resolve_chunk_heading
from app.ingestion.semantic_chunking.types import ChunkMetadata
from app.rag.hybrid.config import HybridRetrievalSettings
from app.rag.hybrid.schemas import SparseSearchHit

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_DEFAULT_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were",
    "will", "with", "this", "these", "those", "or", "not", "but", "what", "which",
    "who", "whom", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "only", "own",
    "same", "so", "than", "too", "very", "can", "could", "should", "would",
})


def _simple_stem(token: str) -> str:
    for suffix in ("ing", "edly", "edly", "ment", "ness", "able", "ible", "ions", "ion", "ies", "es", "ed", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


class BM25Tokenizer:
    """Configurable tokenizer for BM25 indexing and search."""

    def __init__(self, settings: HybridRetrievalSettings) -> None:
        self._settings = settings

    def tokenize(self, text: str) -> list[str]:
        tokens = _TOKEN_RE.findall(text.casefold())
        if self._settings.stopwords_enabled:
            tokens = [token for token in tokens if token not in _DEFAULT_STOPWORDS]
        if self._settings.stemming_enabled:
            tokens = [_simple_stem(token) for token in tokens]
        return tokens


def _indexable_text(chunk: DocumentChunk, settings: HybridRetrievalSettings) -> str:
    """Return the text tokenized for BM25, weighting the chunk's heading when known."""
    if not settings.heading_weighting_enabled:
        return chunk.content
    metadata = chunk.metadata if isinstance(chunk.metadata, ChunkMetadata) else None
    heading = resolve_chunk_heading(
        metadata.section_title if metadata is not None else None,
        metadata.hierarchy_path if metadata is not None else None,
    )
    return build_retrieval_text(
        chunk.content, heading, repetitions=settings.heading_weight_repetitions
    )


class BM25Index:
    """Persistent BM25 index synchronized with semantic chunks."""

    def __init__(
        self,
        *,
        settings: HybridRetrievalSettings,
        persist_path: Path | None = None,
    ) -> None:
        self._settings = settings
        self._tokenizer = BM25Tokenizer(settings)
        self._persist_path = persist_path
        self._chunks: list[DocumentChunk] = []
        self._chunk_ids: list[str] = []
        self._document_ids: list[str | None] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25 = None
        self._last_build_ms: float = 0.0

    @property
    def size(self) -> int:
        return len(self._chunk_ids)

    @property
    def last_build_ms(self) -> float:
        return self._last_build_ms

    @property
    def index_size_bytes(self) -> int:
        return sum(len(tokens) * 8 for tokens in self._tokenized_corpus)

    def _ensure_bm25(self) -> None:
        if self._bm25 is not None or not self._tokenized_corpus:
            return
        from rank_bm25 import BM25Okapi

        self._bm25 = BM25Okapi(
            self._tokenized_corpus,
            k1=self._settings.bm25_k1,
            b=self._settings.bm25_b,
        )

    def _rebuild_bm25(self) -> None:
        started = time.perf_counter()
        self._bm25 = None
        self._ensure_bm25()
        self._last_build_ms = round((time.perf_counter() - started) * 1000, 3)

    def clear(self) -> None:
        self._chunks.clear()
        self._chunk_ids.clear()
        self._document_ids.clear()
        self._tokenized_corpus.clear()
        self._bm25 = None
        if self._persist_path is not None:
            if self._persist_path.exists():
                self._persist_path.unlink()

    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        *,
        document_id: str | None = None,
    ) -> list[str]:
        if not chunks:
            return []
        ids = [chunk.chunk_id for chunk in chunks]
        for chunk in chunks:
            self._chunks.append(chunk)
            self._chunk_ids.append(chunk.chunk_id)
            self._document_ids.append(document_id)
            self._tokenized_corpus.append(
                self._tokenizer.tokenize(_indexable_text(chunk, self._settings))
            )
        self._rebuild_bm25()
        self._persist()
        log_with_fields(
            logger,
            logging.INFO,
            "BM25 index updated",
            document_id=document_id,
            chunks_added=len(chunks),
            total_chunks=self.size,
            build_ms=self._last_build_ms,
        )
        return ids

    def remove_document(self, document_id: str) -> None:
        if not self._chunks:
            return
        retained_chunks: list[DocumentChunk] = []
        retained_ids: list[str] = []
        retained_docs: list[str | None] = []
        retained_tokens: list[list[str]] = []
        for chunk, chunk_id, owner_id, tokens in zip(
            self._chunks,
            self._chunk_ids,
            self._document_ids,
            self._tokenized_corpus,
            strict=True,
        ):
            if owner_id != document_id:
                retained_chunks.append(chunk)
                retained_ids.append(chunk_id)
                retained_docs.append(owner_id)
                retained_tokens.append(tokens)
        if len(retained_chunks) == len(self._chunks):
            return
        self._chunks = retained_chunks
        self._chunk_ids = retained_ids
        self._document_ids = retained_docs
        self._tokenized_corpus = retained_tokens
        self._rebuild_bm25()
        self._persist()

    def rebuild_from_chunks(
        self,
        chunks: list[DocumentChunk],
        *,
        chunk_ids: list[str] | None = None,
        document_ids: list[str | None] | None = None,
    ) -> None:
        """Full rebuild from an existing chunk corpus (evaluation bootstrap path)."""
        self.clear()
        if not chunks:
            return
        ids = chunk_ids or [chunk.chunk_id for chunk in chunks]
        owners = document_ids or [None] * len(chunks)
        for chunk, chunk_id, owner_id in zip(chunks, ids, owners, strict=True):
            self._chunks.append(chunk)
            self._chunk_ids.append(chunk_id)
            self._document_ids.append(owner_id)
            self._tokenized_corpus.append(
                self._tokenizer.tokenize(_indexable_text(chunk, self._settings))
            )
        self._rebuild_bm25()
        self._persist()

    def search(
        self,
        query: str,
        *,
        limit: int,
        allowed_categories: set[str] | None = None,
        allowed_sources: set[str] | None = None,
    ) -> list[SparseSearchHit]:
        if not self._chunks or not query.strip():
            return []
        self._ensure_bm25()
        if self._bm25 is None:
            return []

        query_tokens = self._tokenizer.tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        ranked_indices = sorted(
            range(len(scores)),
            key=lambda index: (-scores[index], self._chunk_ids[index]),
        )

        hits: list[SparseSearchHit] = []
        for rank, index in enumerate(ranked_indices, start=1):
            score = float(scores[index])
            chunk_tokens = set(self._tokenized_corpus[index])
            if not any(token in chunk_tokens for token in query_tokens):
                continue
            chunk = self._chunks[index]
            if allowed_categories and chunk.category not in allowed_categories:
                continue
            if allowed_sources is not None and chunk.source not in allowed_sources:
                continue
            hits.append(
                SparseSearchHit(
                    chunk=chunk,
                    bm25_score=score,
                    rank=rank,
                )
            )
            if len(hits) >= limit:
                break
        return hits

    def _persist(self) -> None:
        if self._persist_path is None:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunk_ids": self._chunk_ids,
            "document_ids": self._document_ids,
            "tokenized_corpus": self._tokenized_corpus,
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "source": chunk.source,
                    "category": chunk.category,
                    "page_number": chunk.page_number,
                }
                for chunk in self._chunks
            ],
        }
        self._persist_path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self) -> bool:
        if self._persist_path is None or not self._persist_path.exists():
            return False
        payload = json.loads(self._persist_path.read_text(encoding="utf-8"))
        self._chunk_ids = list(payload.get("chunk_ids", []))
        self._document_ids = list(payload.get("document_ids", []))
        self._tokenized_corpus = list(payload.get("tokenized_corpus", []))
        self._chunks = []
        for raw in payload.get("chunks", []):
            self._chunks.append(
                DocumentChunk(
                    chunk_id=str(raw["chunk_id"]),
                    content=str(raw["content"]),
                    source=str(raw["source"]),
                    category=str(raw.get("category", "general")),
                    chunk_index=int(raw.get("chunk_index", 0)),
                    page_number=raw.get("page_number"),
                )
            )
        self._rebuild_bm25()
        return True
