"""Graph diagnostics helpers."""

from __future__ import annotations

from app.knowledge_graph.graph.store import InMemoryGraph
from app.knowledge_graph.validators.graph_validator import GraphValidator


class GraphDiagnostics:
    def __init__(self, validator: GraphValidator | None = None) -> None:
        self._validator = validator or GraphValidator()

    def report(self, graph: InMemoryGraph, *, cycles_detected: int = 0) -> dict:
        stats = self._validator.statistics(graph)
        health = self._validator.health(graph, cycles=cycles_detected)
        errors = self._validator.validate(graph)
        return {
            "statistics": stats.to_dict(),
            "health": health.to_dict(),
            "validation_errors": errors,
            "disconnected_nodes": stats.disconnected_nodes,
            "orphan_nodes": stats.orphan_nodes,
            "low_confidence_edges": [
                edge.to_dict()
                for edge in graph.edges()
                if edge.confidence < 0.4
            ][:50],
        }
