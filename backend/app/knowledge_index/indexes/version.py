"""Version group / duplicate / canonical / latest index."""

from __future__ import annotations

import time
from typing import Any

from app.knowledge_index.interfaces.base import KnowledgeIndex
from app.knowledge_index.models.types import IndexDocument, IndexLookupResult, IndexStatistics


class VersionIndex(KnowledgeIndex):
    name = "version"

    def __init__(self) -> None:
        self._docs: dict[str, IndexDocument] = {}
        self._groups: dict[str, set[str]] = {}
        self._duplicates: dict[str, str] = {}  # document_id → duplicate_of knowledge/doc id
        self._latest: dict[str, str] = {}  # group → document_id
        self._canonical: set[str] = set()

    def clear(self) -> None:
        self._docs.clear()
        self._groups.clear()
        self._duplicates.clear()
        self._latest.clear()
        self._canonical.clear()

    def build(self, documents: list[IndexDocument]) -> None:
        self.clear()
        for document in documents:
            self.insert(document)
        self._recompute_latest()

    def insert(self, document: IndexDocument) -> None:
        self.remove(document.document_id)
        self._docs[document.document_id] = document
        if document.version_group_key:
            self._groups.setdefault(document.version_group_key, set()).add(document.document_id)
        if document.probable_duplicate_of:
            self._duplicates[document.document_id] = document.probable_duplicate_of
        if document.is_canonical:
            self._canonical.add(document.document_id)
        self._recompute_latest()

    def remove(self, document_id: str) -> None:
        previous = self._docs.pop(document_id, None)
        if previous is None:
            return
        if previous.version_group_key:
            group = self._groups.get(previous.version_group_key)
            if group is not None:
                group.discard(document_id)
                if not group:
                    self._groups.pop(previous.version_group_key, None)
                    self._latest.pop(previous.version_group_key, None)
        self._duplicates.pop(document_id, None)
        self._canonical.discard(document_id)
        self._recompute_latest()

    def lookup(self, query: Any, **kwargs: Any) -> IndexLookupResult:
        started = time.perf_counter()
        if isinstance(query, dict):
            mode = str(query.get("mode") or kwargs.get("mode") or "group")
            value = query.get("value") or query.get("group") or ""
        else:
            mode = str(kwargs.get("mode") or "group")
            value = query
        mode = mode.strip().lower()
        if mode == "duplicates":
            ids = sorted(self._duplicates.keys())
        elif mode == "canonical":
            ids = sorted(self._canonical)
        elif mode == "latest":
            group = str(value or "")
            latest = self._latest.get(group)
            ids = [latest] if latest else []
        else:
            ids = sorted(self._groups.get(str(value or ""), set()))
        return IndexLookupResult(
            index_name=self.name,
            query={"mode": mode, "value": value},
            document_ids=ids,
            elapsed_ms=(time.perf_counter() - started) * 1000,
            meta={
                "groups": len(self._groups),
                "duplicates": len(self._duplicates),
            },
        )

    def statistics(self) -> IndexStatistics:
        return IndexStatistics(
            name=self.name,
            entry_count=len(self._docs),
            document_count=len(self._docs),
            key_count=len(self._groups),
            memory_bytes_estimate=sum(len(doc_id) for doc_id in self._docs),
            details={
                "version_groups": len(self._groups),
                "duplicates": len(self._duplicates),
                "canonical": len(self._canonical),
                "latest_tracked": len(self._latest),
            },
        )

    def document_ids(self) -> set[str]:
        return set(self._docs.keys())

    def version_info(self, document_id: str) -> dict[str, Any] | None:
        document = self._docs.get(document_id)
        if document is None:
            return None
        return {
            "version_group_key": document.version_group_key,
            "version_label": document.version_label,
            "version_rank": document.version_rank,
            "is_latest_in_group": document.is_latest_in_group
            or self._latest.get(document.version_group_key or "") == document_id,
            "is_canonical": document.is_canonical,
            "probable_duplicate_of": document.probable_duplicate_of,
            "group_members": sorted(self._groups.get(document.version_group_key or "", set())),
        }

    def _recompute_latest(self) -> None:
        self._latest.clear()
        for group, members in self._groups.items():
            best_id = None
            best_rank = -1
            for document_id in members:
                document = self._docs.get(document_id)
                if document is None:
                    continue
                if document.version_rank >= best_rank:
                    best_rank = document.version_rank
                    best_id = document_id
            if best_id:
                self._latest[group] = best_id
                # Refresh flag on stored docs.
                for document_id in members:
                    document = self._docs.get(document_id)
                    if document is not None:
                        document.is_latest_in_group = document_id == best_id
