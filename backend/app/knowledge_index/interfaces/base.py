"""Common interface for Hybrid Knowledge Indexes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.knowledge_index.models.types import IndexDocument, IndexLookupResult, IndexStatistics


class KnowledgeIndex(ABC):
    """Contract every Hybrid Knowledge Index must implement."""

    name: str

    @abstractmethod
    def build(self, documents: list[IndexDocument]) -> None:
        """Replace the index contents with a full rebuild."""

    @abstractmethod
    def insert(self, document: IndexDocument) -> None:
        """Insert or overwrite a single document."""

    @abstractmethod
    def remove(self, document_id: str) -> None:
        """Remove a document from the index."""

    def update(self, document: IndexDocument) -> None:
        """Default update = remove then insert."""
        self.remove(document.document_id)
        self.insert(document)

    @abstractmethod
    def lookup(self, query: Any, **kwargs: Any) -> IndexLookupResult:
        """Lookup documents. Query shape is index-specific."""

    @abstractmethod
    def statistics(self) -> IndexStatistics:
        """Return size / coverage metrics for this index."""

    @abstractmethod
    def clear(self) -> None:
        """Drop all entries."""

    def document_ids(self) -> set[str]:
        """Optional: set of document ids present in this index."""
        return set()


class InvertedKnowledgeIndex(KnowledgeIndex):
    """Shared inverted-index helpers (term → document ids)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._forward: dict[str, set[str]] = {}
        self._inverted: dict[str, set[str]] = {}

    def clear(self) -> None:
        self._forward.clear()
        self._inverted.clear()

    def build(self, documents: list[IndexDocument]) -> None:
        self.clear()
        for document in documents:
            self.insert(document)

    def remove(self, document_id: str) -> None:
        terms = self._forward.pop(document_id, set())
        for term in terms:
            bucket = self._inverted.get(term)
            if not bucket:
                continue
            bucket.discard(document_id)
            if not bucket:
                self._inverted.pop(term, None)

    def document_ids(self) -> set[str]:
        return set(self._forward.keys())

    def _index_terms(self, document_id: str, terms: list[str]) -> None:
        normalized = {self._normalize(term) for term in terms if term}
        normalized.discard("")
        # Replace prior posting for this document.
        self.remove(document_id)
        if not normalized:
            return
        self._forward[document_id] = set(normalized)
        for term in normalized:
            self._inverted.setdefault(term, set()).add(document_id)

    def _lookup_exact(self, query: str) -> list[str]:
        key = self._normalize(query)
        if not key:
            return []
        return sorted(self._inverted.get(key, set()))

    def _lookup_prefix(self, prefix: str) -> list[str]:
        key = self._normalize(prefix)
        if not key:
            return []
        matched: set[str] = set()
        for term, docs in self._inverted.items():
            if term.startswith(key):
                matched.update(docs)
        return sorted(matched)

    @staticmethod
    def _normalize(value: str) -> str:
        return str(value or "").strip().lower()

    def _estimate_memory(self) -> int:
        # Rough estimate: keys + document id strings.
        size = 0
        for term, docs in self._inverted.items():
            size += len(term) + sum(len(doc_id) for doc_id in docs)
        for doc_id, terms in self._forward.items():
            size += len(doc_id) + sum(len(term) for term in terms)
        return size

    def _base_statistics(self, *, details: dict[str, Any] | None = None) -> IndexStatistics:
        return IndexStatistics(
            name=self.name,
            entry_count=sum(len(docs) for docs in self._inverted.values()),
            document_count=len(self._forward),
            key_count=len(self._inverted),
            memory_bytes_estimate=self._estimate_memory(),
            details=details or {},
        )
