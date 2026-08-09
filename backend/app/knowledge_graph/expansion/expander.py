"""Graph expansion services returning GraphEvidence (not documents)."""

from __future__ import annotations

import time

from app.knowledge_graph.graph.store import InMemoryGraph
from app.knowledge_graph.models.enums import EdgeType, NodeType
from app.knowledge_graph.models.types import GraphEvidence, GraphEvidenceItem
from app.knowledge_graph.scoring.scorer import GraphEvidenceScorer
from app.knowledge_graph.traversal.engine import GraphTraverser


class GraphExpander:
    def __init__(
        self,
        *,
        traveller: GraphTraverser | None = None,
        scorer: GraphEvidenceScorer | None = None,
    ) -> None:
        self._traveller = traveller or GraphTraverser()
        self._scorer = scorer or GraphEvidenceScorer()

    def expand(
        self,
        graph: InMemoryGraph,
        seed_ids: list[str],
        *,
        mode: str = "neighbors",
        max_depth: int = 2,
        edge_types: set[str] | None = None,
        min_confidence: float = 0.0,
        budget: int = 80,
    ) -> GraphEvidence:
        started = time.perf_counter()
        warnings: list[str] = []
        items: list[GraphEvidenceItem] = []
        traversals = []

        resolved_edge_types = edge_types
        if mode == "taxonomy":
            resolved_edge_types = {EdgeType.SAME_TAXONOMY.value, EdgeType.BELONGS_TO.value}
        elif mode == "entity":
            resolved_edge_types = {EdgeType.CONTAINS_ENTITY.value, EdgeType.MENTIONS.value}
        elif mode == "department":
            resolved_edge_types = {EdgeType.SAME_DEPARTMENT.value}
        elif mode == "version":
            resolved_edge_types = {
                EdgeType.PREVIOUS_VERSION.value,
                EdgeType.NEXT_VERSION.value,
                EdgeType.DUPLICATE_OF.value,
                EdgeType.BELONGS_TO.value,
            }
        elif mode == "relationship":
            resolved_edge_types = {
                EdgeType.RELATED_TO.value,
                EdgeType.REFERENCES.value,
                EdgeType.GOVERNS.value,
                EdgeType.EXTENDS.value,
                EdgeType.MENTIONS.value,
            }
        elif mode == "neighbors":
            max_depth = 1

        for seed in seed_ids:
            if not graph.has_node(seed):
                warnings.append(f"missing_seed:{seed}")
                continue
            traversal = self._traveller.traverse(
                graph,
                seed,
                max_depth=max_depth,
                budget=budget,
                min_confidence=min_confidence,
                edge_types=resolved_edge_types,
                direction="both",
                weighted=True,
            )
            traversals.append(traversal.to_dict())
            for step in traversal.steps:
                if step.node_id == seed and step.depth == 0:
                    continue
                node = graph.get_node(step.node_id)
                if node is None:
                    continue
                version_priority = 0.0
                if node.type == NodeType.VERSION_GROUP.value:
                    version_priority = 1.0
                if step.via_edge_type in {
                    EdgeType.NEXT_VERSION.value,
                    EdgeType.PREVIOUS_VERSION.value,
                    EdgeType.DUPLICATE_OF.value,
                }:
                    version_priority = 1.0
                item = GraphEvidenceItem(
                    node_id=node.id,
                    node_type=node.type,
                    label=node.label or node.id,
                    edge_type=step.via_edge_type,
                    edge_id=step.via_edge_id,
                    depth=step.depth,
                    confidence=min(0.99, step.cumulative_weight),
                    metadata={"seed": seed, "cumulative_weight": step.cumulative_weight},
                )
                items.append(
                    self._scorer.score_item(
                        item,
                        taxonomy_distance=step.depth if "taxonomy" in (step.via_edge_type or "") else 0,
                        version_priority=version_priority,
                    )
                )

        # Deduplicate by node_id keeping highest score
        best: dict[str, GraphEvidenceItem] = {}
        for item in items:
            existing = best.get(item.node_id)
            if existing is None or item.score > existing.score:
                best[item.node_id] = item
        ranked = sorted(best.values(), key=lambda item: (-item.score, item.node_id))
        return GraphEvidence(
            seed_node_ids=list(seed_ids),
            items=ranked,
            traversal={"runs": traversals},
            contribution_score=self._scorer.contribution(ranked),
            elapsed_ms=(time.perf_counter() - started) * 1000,
            warnings=warnings,
        )
