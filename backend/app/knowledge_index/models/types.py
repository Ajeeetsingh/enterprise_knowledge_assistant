"""Shared types for Hybrid Knowledge Index documents and statistics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RelationshipEdgeRef:
    """Lightweight relationship edge attached to an indexed document."""

    relationship_id: str
    source_knowledge_id: str
    target_knowledge_id: str
    source_document_id: str
    target_document_id: str
    relationship_type: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IndexDocument:
    """Unified indexing unit assembled from KO + Registry + Relationships."""

    document_id: str
    knowledge_id: str
    filename: str = ""
    extension: str = ""
    owner: str | None = None
    upload_date: str | None = None
    document_type: str = "Unknown"
    language: str = "unknown"
    collections: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    taxonomy_path: str = ""
    entities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    version_group_key: str | None = None
    version_label: str | None = None
    version_rank: int = 1
    is_latest_in_group: bool = True
    is_canonical: bool = True
    probable_duplicate_of: str | None = None
    relationships: list[RelationshipEdgeRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IndexDocument:
        edges = [
            RelationshipEdgeRef(**edge) if isinstance(edge, dict) else edge
            for edge in (data.get("relationships") or [])
        ]
        return cls(
            document_id=str(data.get("document_id", "")),
            knowledge_id=str(data.get("knowledge_id", "")),
            filename=str(data.get("filename", "")),
            extension=str(data.get("extension", "")),
            owner=data.get("owner"),
            upload_date=data.get("upload_date"),
            document_type=str(data.get("document_type", "Unknown")),
            language=str(data.get("language", "unknown")),
            collections=list(data.get("collections") or []),
            departments=list(data.get("departments") or []),
            taxonomy_path=str(data.get("taxonomy_path", "")),
            entities=list(data.get("entities") or []),
            keywords=list(data.get("keywords") or []),
            topics=list(data.get("topics") or []),
            tags=list(data.get("tags") or []),
            version_group_key=data.get("version_group_key"),
            version_label=data.get("version_label"),
            version_rank=int(data.get("version_rank") or 1),
            is_latest_in_group=bool(data.get("is_latest_in_group", True)),
            is_canonical=bool(data.get("is_canonical", True)),
            probable_duplicate_of=data.get("probable_duplicate_of"),
            relationships=edges,
        )


@dataclass
class IndexStatistics:
    name: str
    entry_count: int = 0
    document_count: int = 0
    key_count: int = 0
    memory_bytes_estimate: int = 0
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IndexLookupResult:
    index_name: str
    query: Any
    document_ids: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IndexHealth:
    status: str = "healthy"
    documents_indexed: int = 0
    missing_indexes: list[str] = field(default_factory=list)
    missing_metadata: list[str] = field(default_factory=list)
    unindexed_entities: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IndexManagerStatistics:
    index_count: int = 0
    documents_indexed: int = 0
    coverage: float = 0.0
    build_time_ms: float = 0.0
    average_lookup_ms: float = 0.0
    documents_per_sec: float = 0.0
    memory_bytes_estimate: int = 0
    index_size_bytes: int = 0
    index_version: str = ""
    per_index: dict[str, dict[str, Any]] = field(default_factory=dict)
    health: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
