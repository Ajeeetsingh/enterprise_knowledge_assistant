"""Builders that assemble IndexDocument units from Phase 13 artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from app.knowledge_engine.types import DocumentKnowledge, ExtractedEntities
from app.knowledge_index.models.types import IndexDocument, RelationshipEdgeRef
from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.types import KnowledgeRelationshipRecord


def flatten_entities(entities: ExtractedEntities | dict[str, Any] | None) -> list[str]:
    if entities is None:
        return []
    if isinstance(entities, ExtractedEntities):
        data = entities.to_dict() if hasattr(entities, "to_dict") else {
            field: getattr(entities, field) for field in entities.__dataclass_fields__
        }
    else:
        data = entities
    values: list[str] = []
    for items in data.values():
        if isinstance(items, list):
            values.extend(str(item) for item in items if item)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(value.strip())
    return unique


def build_index_document(
    *,
    knowledge: DocumentKnowledge,
    registry: RegistryEntry | None = None,
    relationships: Iterable[KnowledgeRelationshipRecord | RelationshipEdgeRef] | None = None,
    knowledge_id_to_document_id: dict[str, str] | None = None,
) -> IndexDocument:
    """Combine Knowledge Object + Registry + Relationships into one IndexDocument."""
    meta = knowledge.metadata
    filename = meta.filename or (registry.filename if registry else "")
    extension = meta.extension or (Path(filename).suffix.lstrip(".").lower() if filename else "")
    collections = list(registry.collections) if registry else []
    taxonomy_path = registry.taxonomy_path if registry else ""
    departments = list(knowledge.departments)
    if registry and registry.primary_collection and registry.primary_collection not in {
        "unknown",
        "",
    }:
        # Keep KO departments authoritative; collection is separate.
        pass

    id_map = knowledge_id_to_document_id or {}
    knowledge_id = registry.knowledge_id if registry else knowledge.document_id
    document_id = knowledge.document_id
    if registry:
        document_id = registry.document_id or document_id
        id_map = {**id_map, knowledge_id: document_id}

    edges: list[RelationshipEdgeRef] = []
    for rel in relationships or []:
        if isinstance(rel, RelationshipEdgeRef):
            edges.append(rel)
            continue
        source_doc = id_map.get(rel.source_knowledge_id, "")
        target_doc = id_map.get(rel.target_knowledge_id, "")
        edges.append(
            RelationshipEdgeRef(
                relationship_id=str(rel.relationship_id),
                source_knowledge_id=str(rel.source_knowledge_id),
                target_knowledge_id=str(rel.target_knowledge_id),
                source_document_id=source_doc,
                target_document_id=target_doc,
                relationship_type=str(rel.relationship_type),
                confidence=float(rel.confidence),
            )
        )

    return IndexDocument(
        document_id=str(document_id),
        knowledge_id=str(knowledge_id),
        filename=filename,
        extension=extension,
        owner=meta.owner,
        upload_date=meta.upload_date,
        document_type=knowledge.document_type,
        language=knowledge.language or meta.language or "unknown",
        collections=collections,
        departments=departments,
        taxonomy_path=taxonomy_path,
        entities=flatten_entities(knowledge.entities),
        keywords=list(knowledge.keywords),
        topics=list(knowledge.topics),
        tags=list(knowledge.tags),
        version_group_key=registry.version_group_key if registry else None,
        version_label=registry.version_label if registry else None,
        version_rank=int(registry.version_rank) if registry else 1,
        is_latest_in_group=True,
        is_canonical=not bool(registry.probable_duplicate_of) if registry else True,
        probable_duplicate_of=registry.probable_duplicate_of if registry else None,
        relationships=edges,
    )


def build_index_documents(
    *,
    knowledge_objects: list[DocumentKnowledge],
    registry_entries: list[RegistryEntry],
    relationships: list[KnowledgeRelationshipRecord] | None = None,
) -> list[IndexDocument]:
    registry_by_doc = {entry.document_id: entry for entry in registry_entries}
    id_map = {entry.knowledge_id: entry.document_id for entry in registry_entries}
    relationships = relationships or []
    rels_by_source: dict[str, list[KnowledgeRelationshipRecord]] = {}
    for rel in relationships:
        rels_by_source.setdefault(rel.source_knowledge_id, []).append(rel)

    documents: list[IndexDocument] = []
    for knowledge in knowledge_objects:
        registry = registry_by_doc.get(knowledge.document_id)
        knowledge_id = registry.knowledge_id if registry else knowledge.document_id
        docs = build_index_document(
            knowledge=knowledge,
            registry=registry,
            relationships=rels_by_source.get(knowledge_id, []),
            knowledge_id_to_document_id=id_map,
        )
        documents.append(docs)

    # Mark latest in version groups.
    groups: dict[str, list[IndexDocument]] = {}
    for document in documents:
        if document.version_group_key:
            groups.setdefault(document.version_group_key, []).append(document)
    for members in groups.values():
        best = max(members, key=lambda item: item.version_rank)
        for member in members:
            member.is_latest_in_group = member.document_id == best.document_id
    return documents


def knowledge_from_record_json(knowledge_json: str | dict[str, Any]) -> DocumentKnowledge:
    data = json.loads(knowledge_json) if isinstance(knowledge_json, str) else knowledge_json
    return DocumentKnowledge.from_dict(data)
