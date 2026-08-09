"""Deterministic graph evidence scoring."""

from __future__ import annotations

from app.knowledge_graph.models.enums import EdgeType, NodeType
from app.knowledge_graph.models.types import GraphEvidenceItem


_EDGE_SPECIFICITY = {
    EdgeType.DUPLICATE_OF.value: 1.4,
    EdgeType.PREVIOUS_VERSION.value: 1.3,
    EdgeType.NEXT_VERSION.value: 1.3,
    EdgeType.GOVERNS.value: 1.25,
    EdgeType.REFERENCES.value: 1.15,
    EdgeType.MENTIONS.value: 1.05,
    EdgeType.SAME_TAXONOMY.value: 1.2,
    EdgeType.SAME_DEPARTMENT.value: 1.1,
    EdgeType.SAME_COLLECTION.value: 1.05,
    EdgeType.CONTAINS_ENTITY.value: 1.0,
    EdgeType.CONTAINS_TOPIC.value: 0.95,
    EdgeType.RELATED_TO.value: 0.9,
    EdgeType.BELONGS_TO.value: 0.85,
    EdgeType.EXTENDS.value: 1.1,
}


class GraphEvidenceScorer:
    def score_item(
        self,
        item: GraphEvidenceItem,
        *,
        taxonomy_distance: int = 0,
        version_priority: float = 0.0,
    ) -> GraphEvidenceItem:
        depth_penalty = 1.0 / (1.0 + item.depth)
        specificity = _EDGE_SPECIFICITY.get(item.edge_type or "", 0.8)
        node_bonus = 1.15 if item.node_type == NodeType.KNOWLEDGE_OBJECT.value else 1.0
        taxonomy_factor = 1.0 / (1.0 + max(0, taxonomy_distance))
        score = (
            item.confidence
            * specificity
            * depth_penalty
            * node_bonus
            * taxonomy_factor
            * (1.0 + 0.15 * version_priority)
        )
        item.score = round(score, 4)
        item.explanation = (
            f"{item.edge_type or 'node'} @ depth {item.depth} "
            f"(conf={item.confidence:.2f}, specificity={specificity})"
        )
        return item

    def contribution(self, items: list[GraphEvidenceItem]) -> float:
        if not items:
            return 0.0
        return round(sum(item.score for item in items) / max(1, len(items)), 4)
