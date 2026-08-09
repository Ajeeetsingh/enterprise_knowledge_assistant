"""Graph consistency validation and health diagnostics."""

from __future__ import annotations

from collections import Counter, deque

from app.knowledge_graph.graph.store import InMemoryGraph
from app.knowledge_graph.models.types import GraphHealth, GraphStatistics
from app.knowledge_graph.version import KNOWLEDGE_GRAPH_PIPELINE_VERSION


class GraphValidator:
    def statistics(self, graph: InMemoryGraph, *, build_time_ms: float = 0.0) -> GraphStatistics:
        nodes = graph.nodes()
        edges = graph.edges()
        nodes_by_type = dict(Counter(node.type for node in nodes))
        edges_by_type = dict(Counter(edge.type for edge in edges))
        orphan = [node.id for node in nodes if graph.degree(node.id) == 0]
        components = self._connected_components(graph)
        degrees = [graph.degree(node.id) for node in nodes]
        avg_degree = (sum(degrees) / len(degrees)) if degrees else 0.0
        ko_nodes = [node for node in nodes if node.type == "KnowledgeObject"]
        connected_kos = [node for node in ko_nodes if graph.degree(node.id) > 0]
        coverage = (len(connected_kos) / len(ko_nodes)) if ko_nodes else 0.0
        # Disconnected = nodes in singleton components that aren't pure orphans already listed
        disconnected = [
            component[0]
            for component in components
            if len(component) == 1 and component[0] not in orphan
        ]
        return GraphStatistics(
            node_count=len(nodes),
            edge_count=len(edges),
            nodes_by_type=nodes_by_type,
            edges_by_type=edges_by_type,
            connected_components=len(components),
            average_degree=round(avg_degree, 4),
            coverage=round(coverage, 4),
            orphan_nodes=orphan[:50],
            disconnected_nodes=disconnected[:50],
            build_time_ms=round(build_time_ms, 4),
            graph_version=KNOWLEDGE_GRAPH_PIPELINE_VERSION,
        )

    def health(self, graph: InMemoryGraph, *, cycles: int = 0) -> GraphHealth:
        stats = self.statistics(graph)
        low_conf = sum(1 for edge in graph.edges() if edge.confidence < 0.4)
        status = "healthy"
        notes: list[str] = []
        if stats.orphan_nodes:
            notes.append(f"{len(stats.orphan_nodes)} orphan nodes")
            status = "degraded"
        if low_conf:
            notes.append(f"{low_conf} low-confidence edges")
            status = "degraded"
        if cycles:
            notes.append(f"{cycles} cycles observed during traversals")
        if stats.node_count == 0:
            status = "empty"
            notes.append("Graph has no nodes")
        return GraphHealth(
            status=status,
            cycles_detected=cycles,
            low_confidence_edges=low_conf,
            orphan_count=len(stats.orphan_nodes),
            notes=notes,
        )

    def validate(self, graph: InMemoryGraph) -> list[str]:
        errors: list[str] = []
        for edge in graph.edges():
            if not graph.has_node(edge.source):
                errors.append(f"dangling_source:{edge.id}")
            if not graph.has_node(edge.target):
                errors.append(f"dangling_target:{edge.id}")
            if edge.source == edge.target:
                errors.append(f"self_loop:{edge.id}")
        return errors

    def _connected_components(self, graph: InMemoryGraph) -> list[list[str]]:
        remaining = set(graph.node_ids())
        components: list[list[str]] = []
        while remaining:
            start = next(iter(remaining))
            queue = deque([start])
            seen = {start}
            remaining.discard(start)
            while queue:
                node = queue.popleft()
                for neighbor in graph.neighbors(node, direction="both"):
                    if neighbor in remaining:
                        remaining.discard(neighbor)
                        seen.add(neighbor)
                        queue.append(neighbor)
            components.append(sorted(seen))
        return components
