"""Relationship edge index (incoming / outgoing / type). No graph traversal."""

from __future__ import annotations

import time
from typing import Any

from app.knowledge_index.interfaces.base import KnowledgeIndex
from app.knowledge_index.models.types import (
    IndexDocument,
    IndexLookupResult,
    IndexStatistics,
    RelationshipEdgeRef,
)


class RelationshipIndex(KnowledgeIndex):
    name = "relationship"

    def __init__(self) -> None:
        self._by_id: dict[str, RelationshipEdgeRef] = {}
        self._outgoing: dict[str, set[str]] = {}  # knowledge_id → relationship_ids
        self._incoming: dict[str, set[str]] = {}
        self._by_type: dict[str, set[str]] = {}
        self._doc_to_knowledge: dict[str, str] = {}
        self._knowledge_to_doc: dict[str, str] = {}
        self._doc_edges: dict[str, set[str]] = {}

    def clear(self) -> None:
        self._by_id.clear()
        self._outgoing.clear()
        self._incoming.clear()
        self._by_type.clear()
        self._doc_to_knowledge.clear()
        self._knowledge_to_doc.clear()
        self._doc_edges.clear()

    def build(self, documents: list[IndexDocument]) -> None:
        self.clear()
        for document in documents:
            self.insert(document)

    def insert(self, document: IndexDocument) -> None:
        self.remove(document.document_id)
        self._doc_to_knowledge[document.document_id] = document.knowledge_id
        self._knowledge_to_doc[document.knowledge_id] = document.document_id
        edge_ids: set[str] = set()
        for edge in document.relationships:
            self._by_id[edge.relationship_id] = edge
            edge_ids.add(edge.relationship_id)
            self._outgoing.setdefault(edge.source_knowledge_id, set()).add(edge.relationship_id)
            self._incoming.setdefault(edge.target_knowledge_id, set()).add(edge.relationship_id)
            rel_type = (edge.relationship_type or "").strip().lower()
            if rel_type:
                self._by_type.setdefault(rel_type, set()).add(edge.relationship_id)
        self._doc_edges[document.document_id] = edge_ids

    def remove(self, document_id: str) -> None:
        knowledge_id = self._doc_to_knowledge.pop(document_id, None)
        if knowledge_id:
            self._knowledge_to_doc.pop(knowledge_id, None)
        edge_ids = self._doc_edges.pop(document_id, set())
        for edge_id in edge_ids:
            edge = self._by_id.pop(edge_id, None)
            if edge is None:
                continue
            out = self._outgoing.get(edge.source_knowledge_id)
            if out is not None:
                out.discard(edge_id)
                if not out:
                    self._outgoing.pop(edge.source_knowledge_id, None)
            incoming = self._incoming.get(edge.target_knowledge_id)
            if incoming is not None:
                incoming.discard(edge_id)
                if not incoming:
                    self._incoming.pop(edge.target_knowledge_id, None)
            rel_type = (edge.relationship_type or "").strip().lower()
            bucket = self._by_type.get(rel_type)
            if bucket is not None:
                bucket.discard(edge_id)
                if not bucket:
                    self._by_type.pop(rel_type, None)

    def lookup(self, query: Any, **kwargs: Any) -> IndexLookupResult:
        started = time.perf_counter()
        if isinstance(query, dict):
            mode = str(query.get("mode") or kwargs.get("mode") or "outgoing")
            value = query.get("value") or query.get("knowledge_id") or query.get("type") or ""
        else:
            mode = str(kwargs.get("mode") or "outgoing")
            value = query

        mode = mode.strip().lower()
        key = str(value or "").strip()
        edges: list[RelationshipEdgeRef] = []
        if mode == "type":
            for edge_id in self._by_type.get(key.lower(), set()):
                edge = self._by_id.get(edge_id)
                if edge:
                    edges.append(edge)
        elif mode == "incoming":
            knowledge_id = self._resolve_knowledge_id(key)
            for edge_id in self._incoming.get(knowledge_id, set()):
                edge = self._by_id.get(edge_id)
                if edge:
                    edges.append(edge)
        else:  # outgoing
            knowledge_id = self._resolve_knowledge_id(key)
            for edge_id in self._outgoing.get(knowledge_id, set()):
                edge = self._by_id.get(edge_id)
                if edge:
                    edges.append(edge)

        document_ids = sorted(
            {
                edge.target_document_id if mode != "incoming" else edge.source_document_id
                for edge in edges
                if (edge.target_document_id if mode != "incoming" else edge.source_document_id)
            }
        )
        return IndexLookupResult(
            index_name=self.name,
            query={"mode": mode, "value": value},
            document_ids=document_ids,
            elapsed_ms=(time.perf_counter() - started) * 1000,
            meta={"edges": [edge.to_dict() for edge in edges]},
        )

    def statistics(self) -> IndexStatistics:
        memory = sum(len(edge_id) for edge_id in self._by_id) + sum(
            len(k) for k in self._by_type
        )
        return IndexStatistics(
            name=self.name,
            entry_count=len(self._by_id),
            document_count=len(self._doc_edges),
            key_count=len(self._by_type),
            memory_bytes_estimate=memory,
            details={
                "outgoing_sources": len(self._outgoing),
                "incoming_targets": len(self._incoming),
                "types": {k: len(v) for k, v in sorted(self._by_type.items())},
            },
        )

    def document_ids(self) -> set[str]:
        return set(self._doc_edges.keys())

    def edges_for_document(self, document_id: str) -> list[RelationshipEdgeRef]:
        return [
            self._by_id[edge_id]
            for edge_id in self._doc_edges.get(document_id, set())
            if edge_id in self._by_id
        ]

    def _resolve_knowledge_id(self, value: str) -> str:
        if value in self._knowledge_to_doc:
            return value
        if value in self._doc_to_knowledge:
            return self._doc_to_knowledge[value]
        return value
