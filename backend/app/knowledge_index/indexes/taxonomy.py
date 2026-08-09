"""Taxonomy path index with prefix lookup."""

from __future__ import annotations

import time
from typing import Any

from app.knowledge_index.interfaces.base import InvertedKnowledgeIndex
from app.knowledge_index.models.types import IndexDocument, IndexLookupResult


class TaxonomyIndex(InvertedKnowledgeIndex):
    def __init__(self) -> None:
        super().__init__("taxonomy")

    def insert(self, document: IndexDocument) -> None:
        path = (document.taxonomy_path or "").strip()
        terms: list[str] = []
        if path:
            terms.append(path)
            # Also index each path prefix for hierarchical lookup.
            parts = [part for part in path.split("/") if part]
            built: list[str] = []
            for part in parts:
                built.append(part)
                terms.append("/".join(built))
        self._index_terms(document.document_id, terms)

    def lookup(self, query: Any, **kwargs: Any) -> IndexLookupResult:
        started = time.perf_counter()
        if isinstance(query, dict):
            mode = str(query.get("mode") or kwargs.get("mode") or "prefix")
            value = query.get("value") or query.get("path") or ""
        else:
            mode = str(kwargs.get("mode") or "prefix")
            value = query
        if mode == "exact":
            ids = self._lookup_exact(str(value or ""))
        else:
            ids = self._lookup_prefix(str(value or ""))
        return IndexLookupResult(
            index_name=self.name,
            query={"mode": mode, "value": value},
            document_ids=ids,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )

    def statistics(self):
        return self._base_statistics()
