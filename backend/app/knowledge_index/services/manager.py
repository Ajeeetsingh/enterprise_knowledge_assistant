"""KnowledgeIndexManager — orchestrates all Hybrid Knowledge Indexes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from app.knowledge_index.indexes import (
    CollectionIndex,
    DepartmentIndex,
    EntityIndex,
    KeywordIndex,
    MetadataIndex,
    RelationshipIndex,
    TagIndex,
    TaxonomyIndex,
    TopicIndex,
    VersionIndex,
)
from app.knowledge_index.interfaces.base import KnowledgeIndex
from app.knowledge_index.metrics.timing import LookupTimer, Stopwatch
from app.knowledge_index.models.types import (
    IndexDocument,
    IndexLookupResult,
    IndexManagerStatistics,
)
from app.knowledge_index.storage.json_store import KnowledgeIndexJsonStore
from app.knowledge_index.validators.coverage import validate_coverage
from app.knowledge_index.version import KNOWLEDGE_INDEX_PIPELINE_VERSION


def default_indexes() -> dict[str, KnowledgeIndex]:
    return {
        "metadata": MetadataIndex(),
        "collection": CollectionIndex(),
        "department": DepartmentIndex(),
        "taxonomy": TaxonomyIndex(),
        "entity": EntityIndex(),
        "keyword": KeywordIndex(),
        "topic": TopicIndex(),
        "tag": TagIndex(),
        "relationship": RelationshipIndex(),
        "version": VersionIndex(),
    }


class KnowledgeIndexManager:
    """Build, rebuild, incrementally update, validate, and inspect indexes."""

    def __init__(
        self,
        *,
        indexes: dict[str, KnowledgeIndex] | None = None,
        store: KnowledgeIndexJsonStore | None = None,
    ) -> None:
        self._indexes = indexes or default_indexes()
        self._documents: dict[str, IndexDocument] = {}
        self._store = store
        self._last_build_ms = 0.0
        self._lookup_timer = LookupTimer()
        self.index_version = KNOWLEDGE_INDEX_PIPELINE_VERSION

    @property
    def indexes(self) -> dict[str, KnowledgeIndex]:
        return self._indexes

    @property
    def documents(self) -> dict[str, IndexDocument]:
        return self._documents

    def build(self, documents: Iterable[IndexDocument]) -> IndexManagerStatistics:
        watch = Stopwatch()
        docs = list(documents)
        self._documents = {document.document_id: document for document in docs}
        for index in self._indexes.values():
            index.build(docs)
        self._last_build_ms = watch.elapsed_ms()
        stats = self.statistics()
        self._persist(stats)
        return stats

    def rebuild(self) -> IndexManagerStatistics:
        return self.build(list(self._documents.values()))

    def insert(self, document: IndexDocument) -> None:
        self._documents[document.document_id] = document
        for index in self._indexes.values():
            index.insert(document)

    def update(self, document: IndexDocument) -> None:
        self._documents[document.document_id] = document
        for index in self._indexes.values():
            index.update(document)

    def remove(self, document_id: str) -> None:
        self._documents.pop(document_id, None)
        for index in self._indexes.values():
            index.remove(document_id)

    def lookup(self, index_name: str, query: Any, **kwargs: Any) -> IndexLookupResult:
        index = self._indexes.get(index_name)
        if index is None:
            return IndexLookupResult(
                index_name=index_name,
                query=query,
                document_ids=[],
                meta={"error": "unknown_index"},
            )
        result = index.lookup(query, **kwargs)
        self._lookup_timer.record(result.elapsed_ms)
        return result

    def inspect(self, document_id: str) -> dict[str, Any] | None:
        document = self._documents.get(document_id)
        if document is None:
            return None
        metadata_index = self._indexes.get("metadata")
        relationship_index = self._indexes.get("relationship")
        version_index = self._indexes.get("version")
        return {
            "document": document.to_dict(),
            "metadata": metadata_index.get_metadata(document_id)  # type: ignore[attr-defined]
            if metadata_index and hasattr(metadata_index, "get_metadata")
            else None,
            "collection": document.collections,
            "department": document.departments,
            "taxonomy": document.taxonomy_path,
            "entities": document.entities,
            "keywords": document.keywords,
            "topics": document.topics,
            "tags": document.tags,
            "relationships": [
                edge.to_dict()
                for edge in (
                    relationship_index.edges_for_document(document_id)  # type: ignore[attr-defined]
                    if relationship_index and hasattr(relationship_index, "edges_for_document")
                    else document.relationships
                )
            ],
            "version": version_index.version_info(document_id)  # type: ignore[attr-defined]
            if version_index and hasattr(version_index, "version_info")
            else None,
            "index_references": {
                name: document_id in index.document_ids()
                for name, index in self._indexes.items()
            },
        }

    def health(self):
        return validate_coverage(indexes=self._indexes, documents=list(self._documents.values()))

    def statistics(self) -> IndexManagerStatistics:
        per_index = {name: index.statistics().to_dict() for name, index in self._indexes.items()}
        memory = sum(int(stats.get("memory_bytes_estimate") or 0) for stats in per_index.values())
        docs = len(self._documents)
        docs_per_sec = 0.0
        if self._last_build_ms > 0 and docs:
            docs_per_sec = docs / (self._last_build_ms / 1000.0)
        health = self.health()
        coverage = 1.0 if docs and not health.missing_metadata and not health.missing_indexes else (
            0.0 if not docs else max(0.0, 1.0 - (len(health.missing_metadata) / docs))
        )
        store_size = self._store.size_bytes() if self._store else 0
        return IndexManagerStatistics(
            index_count=len(self._indexes),
            documents_indexed=docs,
            coverage=round(coverage, 4),
            build_time_ms=round(self._last_build_ms, 3),
            average_lookup_ms=round(self._lookup_timer.average_ms, 4),
            documents_per_sec=round(docs_per_sec, 2),
            memory_bytes_estimate=memory,
            index_size_bytes=store_size,
            index_version=self.index_version,
            per_index=per_index,
            health=health.to_dict(),
        )

    def snapshot_payload(self) -> dict[str, Any]:
        stats = self.statistics()
        return {
            "pipeline_version": self.index_version,
            "statistics": stats.to_dict(),
            "documents": [document.to_dict() for document in self._documents.values()],
        }

    def _persist(self, stats: IndexManagerStatistics | None = None) -> None:
        if self._store is None:
            return
        payload = self.snapshot_payload()
        if stats is not None:
            payload["statistics"] = stats.to_dict()
        self._store.save(payload)

    @classmethod
    def with_default_store(cls, indexes_root: Path) -> KnowledgeIndexManager:
        store = KnowledgeIndexJsonStore(Path(indexes_root) / "knowledge_index")
        return cls(store=store)
