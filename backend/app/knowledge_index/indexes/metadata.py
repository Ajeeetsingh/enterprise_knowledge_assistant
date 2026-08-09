"""Exact-match metadata index (filename, extension, owner, dates, type, language)."""

from __future__ import annotations

import time
from typing import Any

from app.knowledge_index.interfaces.base import KnowledgeIndex
from app.knowledge_index.models.types import IndexDocument, IndexLookupResult, IndexStatistics


class MetadataIndex(KnowledgeIndex):
    name = "metadata"

    FIELDS = ("filename", "extension", "owner", "upload_date", "document_type", "language")

    def __init__(self) -> None:
        self._by_field: dict[str, dict[str, set[str]]] = {field: {} for field in self.FIELDS}
        self._docs: dict[str, dict[str, str | None]] = {}

    def clear(self) -> None:
        self._by_field = {field: {} for field in self.FIELDS}
        self._docs.clear()

    def build(self, documents: list[IndexDocument]) -> None:
        self.clear()
        for document in documents:
            self.insert(document)

    def insert(self, document: IndexDocument) -> None:
        self.remove(document.document_id)
        values = {
            "filename": document.filename,
            "extension": document.extension,
            "owner": document.owner,
            "upload_date": document.upload_date,
            "document_type": document.document_type,
            "language": document.language,
        }
        self._docs[document.document_id] = values
        for field, raw in values.items():
            key = self._normalize(raw)
            if not key:
                continue
            self._by_field[field].setdefault(key, set()).add(document.document_id)

    def remove(self, document_id: str) -> None:
        previous = self._docs.pop(document_id, None)
        if previous is None:
            return
        for field, raw in previous.items():
            key = self._normalize(raw)
            bucket = self._by_field[field].get(key)
            if not bucket:
                continue
            bucket.discard(document_id)
            if not bucket:
                self._by_field[field].pop(key, None)

    def lookup(self, query: Any, **kwargs: Any) -> IndexLookupResult:
        started = time.perf_counter()
        field = str(kwargs.get("field") or (query.get("field") if isinstance(query, dict) else "") or "")
        value = kwargs.get("value")
        if value is None and isinstance(query, dict):
            value = query.get("value")
        elif value is None and not isinstance(query, dict):
            value = query
        field = field.strip().lower()
        if field not in self.FIELDS:
            return IndexLookupResult(
                index_name=self.name,
                query={"field": field, "value": value},
                document_ids=[],
                elapsed_ms=(time.perf_counter() - started) * 1000,
                meta={"error": "unknown_field"},
            )
        key = self._normalize(value)
        ids = sorted(self._by_field[field].get(key, set())) if key else []
        return IndexLookupResult(
            index_name=self.name,
            query={"field": field, "value": value},
            document_ids=ids,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )

    def statistics(self) -> IndexStatistics:
        key_count = sum(len(mapping) for mapping in self._by_field.values())
        memory = sum(
            len(field) + len(key) + sum(len(doc) for doc in docs)
            for field, mapping in self._by_field.items()
            for key, docs in mapping.items()
        )
        return IndexStatistics(
            name=self.name,
            entry_count=sum(len(docs) for mapping in self._by_field.values() for docs in mapping.values()),
            document_count=len(self._docs),
            key_count=key_count,
            memory_bytes_estimate=memory,
            details={field: len(mapping) for field, mapping in self._by_field.items()},
        )

    def document_ids(self) -> set[str]:
        return set(self._docs.keys())

    def get_metadata(self, document_id: str) -> dict[str, str | None] | None:
        return self._docs.get(document_id)

    @staticmethod
    def _normalize(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()
