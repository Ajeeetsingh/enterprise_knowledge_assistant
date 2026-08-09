"""Collection inverted index."""

from __future__ import annotations

import time
from typing import Any

from app.knowledge_index.interfaces.base import InvertedKnowledgeIndex
from app.knowledge_index.models.types import IndexDocument, IndexLookupResult


class CollectionIndex(InvertedKnowledgeIndex):
    def __init__(self) -> None:
        super().__init__("collection")

    def insert(self, document: IndexDocument) -> None:
        self._index_terms(document.document_id, list(document.collections))

    def lookup(self, query: Any, **kwargs: Any) -> IndexLookupResult:
        started = time.perf_counter()
        value = query.get("value") if isinstance(query, dict) else query
        ids = self._lookup_exact(str(value or ""))
        return IndexLookupResult(
            index_name=self.name,
            query=value,
            document_ids=ids,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )

    def statistics(self):
        return self._base_statistics()
