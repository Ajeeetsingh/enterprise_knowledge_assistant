"""In-memory Knowledge Graph store with incremental updates."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from app.knowledge_graph.models.types import GraphEdge, GraphNode


class InMemoryGraph:
    """Adjacency-list graph. No external graph database."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._out: dict[str, set[str]] = defaultdict(set)
        self._in: dict[str, set[str]] = defaultdict(set)

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._out.clear()
        self._in.clear()

    def upsert_node(self, node: GraphNode) -> None:
        self._nodes[node.id] = node

    def upsert_edge(self, edge: GraphEdge) -> None:
        # Replace prior edge id if present
        previous = self._edges.get(edge.id)
        if previous is not None:
            self._out[previous.source].discard(previous.id)
            self._in[previous.target].discard(previous.id)
        self._edges[edge.id] = edge
        self._out[edge.source].add(edge.id)
        self._in[edge.target].add(edge.id)

    def remove_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)
        for edge_id in list(self._out.get(node_id, set()) | self._in.get(node_id, set())):
            self.remove_edge(edge_id)
        self._out.pop(node_id, None)
        self._in.pop(node_id, None)

    def remove_edge(self, edge_id: str) -> None:
        edge = self._edges.pop(edge_id, None)
        if edge is None:
            return
        self._out[edge.source].discard(edge_id)
        self._in[edge.target].discard(edge_id)

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        return self._edges.get(edge_id)

    def nodes(self) -> list[GraphNode]:
        return list(self._nodes.values())

    def edges(self) -> list[GraphEdge]:
        return list(self._edges.values())

    def outgoing_edges(self, node_id: str) -> list[GraphEdge]:
        return [self._edges[edge_id] for edge_id in self._out.get(node_id, set()) if edge_id in self._edges]

    def incoming_edges(self, node_id: str) -> list[GraphEdge]:
        return [self._edges[edge_id] for edge_id in self._in.get(node_id, set()) if edge_id in self._edges]

    def neighbors(self, node_id: str, *, direction: str = "both") -> list[str]:
        ids: set[str] = set()
        if direction in {"out", "both"}:
            for edge in self.outgoing_edges(node_id):
                ids.add(edge.target)
        if direction in {"in", "both"}:
            for edge in self.incoming_edges(node_id):
                ids.add(edge.source)
        return sorted(ids)

    def degree(self, node_id: str) -> int:
        return len(self._out.get(node_id, set())) + len(self._in.get(node_id, set()))

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def node_ids(self) -> set[str]:
        return set(self._nodes.keys())

    def add_nodes(self, nodes: Iterable[GraphNode]) -> None:
        for node in nodes:
            self.upsert_node(node)

    def add_edges(self, edges: Iterable[GraphEdge]) -> None:
        for edge in edges:
            self.upsert_edge(edge)
