"""Coverage / consistency validators for Hybrid Knowledge Indexes."""

from __future__ import annotations

from app.knowledge_index.interfaces.base import KnowledgeIndex
from app.knowledge_index.models.types import IndexDocument, IndexHealth


REQUIRED_INDEXES = (
    "metadata",
    "collection",
    "department",
    "taxonomy",
    "entity",
    "keyword",
    "topic",
    "tag",
    "relationship",
    "version",
)


def validate_coverage(
    *,
    indexes: dict[str, KnowledgeIndex],
    documents: list[IndexDocument],
) -> IndexHealth:
    missing_indexes = [name for name in REQUIRED_INDEXES if name not in indexes]
    expected_ids = {document.document_id for document in documents}
    missing_metadata: list[str] = []
    unindexed_entities: list[str] = []

    metadata = indexes.get("metadata")
    entity = indexes.get("entity")
    for document in documents:
        if metadata and document.document_id not in metadata.document_ids():
            missing_metadata.append(document.document_id)
        if entity:
            indexed = entity.document_ids()
            if document.entities and document.document_id not in indexed:
                unindexed_entities.append(document.document_id)

    notes: list[str] = []
    if not expected_ids:
        notes.append("No documents indexed.")
    status = "healthy"
    if missing_indexes or missing_metadata or unindexed_entities:
        status = "degraded"
    if missing_indexes:
        status = "unhealthy"

    return IndexHealth(
        status=status,
        documents_indexed=len(expected_ids),
        missing_indexes=missing_indexes,
        missing_metadata=missing_metadata[:50],
        unindexed_entities=unindexed_entities[:50],
        notes=notes,
    )
