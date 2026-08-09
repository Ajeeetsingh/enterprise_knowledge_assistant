"""Depth-limited, filtered, budgeted graph traversal with cycle detection."""

from __future__ import annotations

import time
from collections import deque

from app.knowledge_graph.graph.store import InMemoryGraph
from app.knowledge_graph.models.types import TraversalResult, TraversalStep


class GraphTraverser:
    def traverse(
        self,
        graph: InMemoryGraph,
        root_id: str,
        *,
        max_depth: int = 2,
        budget: int = 100,
        min_confidence: float = 0.0,
        edge_types: set[str] | None = None,
        node_types: set[str] | None = None,
        direction: str = "out",
        weighted: bool = True,
    ) -> TraversalResult:
        started = time.perf_counter()
        if not graph.has_node(root_id):
            return TraversalResult(
                root_id=root_id,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                diagnostics={"error": "unknown_root"},
            )

        max_depth = max(0, min(max_depth, 8))
        budget = max(1, min(budget, 500))
        visited: set[str] = {root_id}
        steps: list[TraversalStep] = [
            TraversalStep(depth=0, node_id=root_id, cumulative_weight=1.0)
        ]
        edges_used: list[str] = []
        cycles: list[str] = []
        truncated = False

        queue: deque[tuple[str, int, float, set[str]]] = deque()
        queue.append((root_id, 0, 1.0, {root_id}))

        while queue:
            if len(visited) >= budget:
                truncated = True
                break
            node_id, depth, weight, path = queue.popleft()
            if depth >= max_depth:
                continue
            edges = []
            if direction in {"out", "both"}:
                edges.extend(graph.outgoing_edges(node_id))
            if direction in {"in", "both"}:
                edges.extend(graph.incoming_edges(node_id))

            # Prefer higher weight edges first when weighted
            if weighted:
                edges = sorted(edges, key=lambda edge: edge.weight * edge.confidence, reverse=True)

            for edge in edges:
                if edge.confidence < min_confidence:
                    continue
                if edge_types and edge.type not in edge_types:
                    continue
                neighbor = edge.target if edge.source == node_id else edge.source
                neighbor_node = graph.get_node(neighbor)
                if neighbor_node is None:
                    continue
                if node_types and neighbor_node.type not in node_types:
                    continue
                if neighbor in path:
                    cycles.append(f"{node_id}->{neighbor}")
                    continue
                next_weight = weight * (edge.weight if weighted else 1.0) * max(edge.confidence, 0.1)
                edges_used.append(edge.id)
                steps.append(
                    TraversalStep(
                        depth=depth + 1,
                        node_id=neighbor,
                        via_edge_id=edge.id,
                        via_edge_type=edge.type,
                        cumulative_weight=round(next_weight, 6),
                    )
                )
                if neighbor not in visited:
                    visited.add(neighbor)
                    if len(visited) >= budget:
                        truncated = True
                        break
                    queue.append((neighbor, depth + 1, next_weight, path | {neighbor}))
            if truncated:
                break

        return TraversalResult(
            root_id=root_id,
            steps=steps,
            visited_nodes=sorted(visited),
            edges_used=edges_used,
            cycles_detected=cycles,
            truncated=truncated,
            elapsed_ms=(time.perf_counter() - started) * 1000,
            diagnostics={
                "max_depth": max_depth,
                "budget": budget,
                "min_confidence": min_confidence,
                "direction": direction,
            },
        )

    def neighbors(
        self,
        graph: InMemoryGraph,
        node_id: str,
        *,
        edge_types: set[str] | None = None,
        direction: str = "both",
    ) -> list[str]:
        result = self.traverse(
            graph,
            node_id,
            max_depth=1,
            budget=100,
            edge_types=edge_types,
            direction=direction,
        )
        return [node for node in result.visited_nodes if node != node_id]
