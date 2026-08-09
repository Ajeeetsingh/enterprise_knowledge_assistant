"""Department label index (single / multi / canonical)."""

from __future__ import annotations

import time
from typing import Any

from app.knowledge_index.interfaces.base import InvertedKnowledgeIndex
from app.knowledge_index.models.types import IndexDocument, IndexLookupResult


class DepartmentIndex(InvertedKnowledgeIndex):
    def __init__(self) -> None:
        super().__init__("department")
        self._multi_label: set[str] = set()

    def clear(self) -> None:
        super().clear()
        self._multi_label.clear()

    def insert(self, document: IndexDocument) -> None:
        departments = list(document.departments)
        self._index_terms(document.document_id, departments)
        if len(departments) > 1:
            self._multi_label.add(document.document_id)
        else:
            self._multi_label.discard(document.document_id)

    def remove(self, document_id: str) -> None:
        super().remove(document_id)
        self._multi_label.discard(document_id)

    def lookup(self, query: Any, **kwargs: Any) -> IndexLookupResult:
        started = time.perf_counter()
        if isinstance(query, dict):
            mode = str(query.get("mode") or kwargs.get("mode") or "exact")
            value = query.get("value")
        else:
            mode = str(kwargs.get("mode") or "exact")
            value = query
        if mode == "multi":
            ids = sorted(self._multi_label)
        else:
            ids = self._lookup_exact(str(value or ""))
        return IndexLookupResult(
            index_name=self.name,
            query={"mode": mode, "value": value},
            document_ids=ids,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )

    def statistics(self):
        return self._base_statistics(
            details={"multi_label_documents": len(self._multi_label)},
        )
