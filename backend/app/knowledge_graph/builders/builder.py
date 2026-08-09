"""Build an in-memory Knowledge Graph from Registry + Relationships + Index docs."""

from __future__ import annotations

import time
import uuid
from typing import Iterable

from app.knowledge_graph.graph.store import InMemoryGraph
from app.knowledge_graph.models.enums import EdgeType, NodeType
from app.knowledge_graph.models.types import GraphEdge, GraphNode, utc_now_iso
from app.knowledge_index.models.types import IndexDocument
from app.knowledge_registry.types import RegistryEntry
from app.knowledge_relationships.types import KnowledgeRelationshipRecord


def _node_id(kind: str, value: str) -> str:
    return f"{kind}:{value}"


class KnowledgeGraphBuilder:
    """Construct graph nodes/edges without PDFs or embeddings."""

    def build(
        self,
        *,
        registry_entries: list[RegistryEntry],
        relationships: list[KnowledgeRelationshipRecord] | None = None,
        index_documents: list[IndexDocument] | None = None,
        graph: InMemoryGraph | None = None,
    ) -> InMemoryGraph:
        started = time.perf_counter()
        store = graph or InMemoryGraph()
        store.clear()
        self._add_registry(store, registry_entries)
        if index_documents:
            self._add_index_documents(store, index_documents)
        if relationships:
            self._add_relationships(store, relationships)
        # stash build time on a synthetic meta node property via side channel is awkward;
        # callers measure separately. Keep builder pure.
        _ = started
        return store

    def upsert_entry(
        self,
        graph: InMemoryGraph,
        entry: RegistryEntry,
        *,
        index_document: IndexDocument | None = None,
        relationships: Iterable[KnowledgeRelationshipRecord] | None = None,
    ) -> None:
        self._add_registry(graph, [entry])
        if index_document is not None:
            self._add_index_documents(graph, [index_document])
        if relationships:
            self._add_relationships(graph, list(relationships))

    def _add_registry(self, graph: InMemoryGraph, entries: list[RegistryEntry]) -> None:
        now = utc_now_iso()
        for entry in entries:
            ko_id = _node_id("ko", entry.knowledge_id)
            graph.upsert_node(
                GraphNode(
                    id=ko_id,
                    type=NodeType.KNOWLEDGE_OBJECT.value,
                    label=entry.filename,
                    metadata={
                        "document_id": entry.document_id,
                        "knowledge_id": entry.knowledge_id,
                        "health": entry.health,
                    },
                    properties={
                        "filename": entry.filename,
                        "primary_collection": entry.primary_collection,
                        "taxonomy_path": entry.taxonomy_path,
                        "version_group_key": entry.version_group_key,
                        "version_rank": entry.version_rank,
                    },
                )
            )
            for collection in entry.collections or [entry.primary_collection]:
                if not collection or collection == "unknown":
                    continue
                cid = _node_id("collection", collection.lower())
                graph.upsert_node(
                    GraphNode(
                        id=cid,
                        type=NodeType.COLLECTION.value,
                        label=collection,
                        properties={"slug": collection.lower()},
                    )
                )
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ko_id}-belongs-{cid}")),
                        type=EdgeType.BELONGS_TO.value,
                        source=ko_id,
                        target=cid,
                        confidence=0.9,
                        evidence=[f"registry collection {collection}"],
                        weight=1.0,
                        timestamp=now,
                    )
                )
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{cid}-sc-{ko_id}")),
                        type=EdgeType.SAME_COLLECTION.value,
                        source=cid,
                        target=ko_id,
                        confidence=0.85,
                        evidence=["collection membership"],
                        weight=0.9,
                        timestamp=now,
                    )
                )

            if entry.taxonomy_path:
                tid = _node_id("taxonomy", entry.taxonomy_path)
                graph.upsert_node(
                    GraphNode(
                        id=tid,
                        type=NodeType.TAXONOMY.value,
                        label=entry.taxonomy_path,
                        properties={"path": entry.taxonomy_path},
                    )
                )
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ko_id}-tax-{tid}")),
                        type=EdgeType.SAME_TAXONOMY.value,
                        source=ko_id,
                        target=tid,
                        confidence=0.88,
                        evidence=[f"taxonomy {entry.taxonomy_path}"],
                        weight=1.1,
                        timestamp=now,
                    )
                )

            if entry.version_group_key:
                vid = _node_id("version", entry.version_group_key)
                graph.upsert_node(
                    GraphNode(
                        id=vid,
                        type=NodeType.VERSION_GROUP.value,
                        label=entry.version_group_key,
                        properties={"group": entry.version_group_key},
                    )
                )
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ko_id}-vg-{vid}")),
                        type=EdgeType.BELONGS_TO.value,
                        source=ko_id,
                        target=vid,
                        confidence=0.9,
                        evidence=["version group"],
                        weight=1.0,
                        timestamp=now,
                        metadata={"version_rank": entry.version_rank, "version_label": entry.version_label},
                    )
                )

            if entry.probable_duplicate_of:
                target = _node_id("ko", entry.probable_duplicate_of)
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ko_id}-dup-{target}")),
                        type=EdgeType.DUPLICATE_OF.value,
                        source=ko_id,
                        target=target,
                        confidence=float(entry.duplicate_score or 0.7),
                        evidence=["registry duplicate signal"],
                        weight=1.2,
                        timestamp=now,
                    )
                )

    def _add_index_documents(self, graph: InMemoryGraph, documents: list[IndexDocument]) -> None:
        now = utc_now_iso()
        for document in documents:
            ko_id = _node_id("ko", document.knowledge_id)
            if not graph.has_node(ko_id):
                graph.upsert_node(
                    GraphNode(
                        id=ko_id,
                        type=NodeType.KNOWLEDGE_OBJECT.value,
                        label=document.filename,
                        metadata={
                            "document_id": document.document_id,
                            "knowledge_id": document.knowledge_id,
                        },
                        properties={"filename": document.filename},
                    )
                )
            if document.document_type:
                dt_id = _node_id("doctype", document.document_type.lower())
                graph.upsert_node(
                    GraphNode(
                        id=dt_id,
                        type=NodeType.DOCUMENT_TYPE.value,
                        label=document.document_type,
                    )
                )
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ko_id}-type-{dt_id}")),
                        type=EdgeType.BELONGS_TO.value,
                        source=ko_id,
                        target=dt_id,
                        confidence=0.8,
                        evidence=["document type"],
                        weight=0.8,
                        timestamp=now,
                    )
                )
            for department in document.departments:
                did = _node_id("department", department.lower())
                graph.upsert_node(
                    GraphNode(
                        id=did,
                        type=NodeType.DEPARTMENT.value,
                        label=department,
                    )
                )
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ko_id}-dept-{did}")),
                        type=EdgeType.SAME_DEPARTMENT.value,
                        source=ko_id,
                        target=did,
                        confidence=0.86,
                        evidence=[f"department {department}"],
                        weight=1.0,
                        timestamp=now,
                    )
                )
            for entity in document.entities:
                eid = _node_id("entity", entity.lower())
                graph.upsert_node(
                    GraphNode(id=eid, type=NodeType.ENTITY.value, label=entity)
                )
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ko_id}-ent-{eid}")),
                        type=EdgeType.CONTAINS_ENTITY.value,
                        source=ko_id,
                        target=eid,
                        confidence=0.75,
                        evidence=[f"entity {entity}"],
                        weight=0.9,
                        timestamp=now,
                    )
                )
            for topic in document.topics:
                tid = _node_id("topic", topic.lower())
                graph.upsert_node(
                    GraphNode(id=tid, type=NodeType.TOPIC.value, label=topic)
                )
                graph.upsert_edge(
                    GraphEdge(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{ko_id}-topic-{tid}")),
                        type=EdgeType.CONTAINS_TOPIC.value,
                        source=ko_id,
                        target=tid,
                        confidence=0.75,
                        evidence=[f"topic {topic}"],
                        weight=0.9,
                        timestamp=now,
                    )
                )

    def _add_relationships(
        self,
        graph: InMemoryGraph,
        relationships: list[KnowledgeRelationshipRecord],
    ) -> None:
        now = utc_now_iso()
        allowed = {item.value for item in EdgeType}
        for rel in relationships:
            source = _node_id("ko", rel.source_knowledge_id)
            target = _node_id("ko", rel.target_knowledge_id)
            if not graph.has_node(source):
                graph.upsert_node(
                    GraphNode(
                        id=source,
                        type=NodeType.KNOWLEDGE_OBJECT.value,
                        label=rel.source_knowledge_id,
                        metadata={"knowledge_id": rel.source_knowledge_id},
                    )
                )
            if not graph.has_node(target):
                graph.upsert_node(
                    GraphNode(
                        id=target,
                        type=NodeType.KNOWLEDGE_OBJECT.value,
                        label=rel.target_knowledge_id,
                        metadata={"knowledge_id": rel.target_knowledge_id},
                    )
                )
            edge_type = rel.relationship_type if rel.relationship_type in allowed else EdgeType.RELATED_TO.value
            evidence = [item.evidence for item in (rel.evidence or [])]
            graph.upsert_edge(
                GraphEdge(
                    id=str(rel.relationship_id),
                    type=edge_type,
                    source=source,
                    target=target,
                    confidence=float(rel.confidence or 0.5),
                    evidence=evidence,
                    weight=max(0.1, float(rel.confidence or 0.5) * 1.2),
                    timestamp=now,
                    metadata={"evidence_source": rel.evidence_source},
                )
            )
