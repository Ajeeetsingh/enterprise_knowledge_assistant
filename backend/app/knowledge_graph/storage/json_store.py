"""Optional JSON snapshot for Knowledge Graph (future persistence abstraction)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.knowledge_graph.graph.store import InMemoryGraph
from app.knowledge_graph.models.types import GraphEdge, GraphNode


class GraphJsonStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot_path = self.root / "knowledge_graph.json"

    def save(self, graph: InMemoryGraph, *, meta: dict[str, Any] | None = None) -> Path:
        payload = {
            "meta": meta or {},
            "nodes": [node.to_dict() for node in graph.nodes()],
            "edges": [edge.to_dict() for edge in graph.edges()],
        }
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.snapshot_path

    def load_into(self, graph: InMemoryGraph) -> bool:
        if not self.snapshot_path.exists():
            return False
        payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        graph.clear()
        for node in payload.get("nodes") or []:
            graph.upsert_node(GraphNode(**node))
        for edge in payload.get("edges") or []:
            graph.upsert_edge(GraphEdge(**edge))
        return True
