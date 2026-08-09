"""Canonical Knowledge Graph domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class GraphNode:
    id: str
    type: str
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    id: str
    type: str
    source: str
    target: str
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    weight: float = 1.0
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TraversalStep:
    depth: int
    node_id: str
    via_edge_id: str | None = None
    via_edge_type: str | None = None
    cumulative_weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TraversalResult:
    root_id: str
    steps: list[TraversalStep] = field(default_factory=list)
    visited_nodes: list[str] = field(default_factory=list)
    edges_used: list[str] = field(default_factory=list)
    cycles_detected: list[str] = field(default_factory=list)
    truncated: bool = False
    elapsed_ms: float = 0.0
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_id": self.root_id,
            "steps": [step.to_dict() for step in self.steps],
            "visited_nodes": self.visited_nodes,
            "edges_used": self.edges_used,
            "cycles_detected": self.cycles_detected,
            "truncated": self.truncated,
            "elapsed_ms": self.elapsed_ms,
            "diagnostics": self.diagnostics,
        }


@dataclass
class GraphEvidenceItem:
    """Graph expansion evidence — not a document retrieval hit."""

    node_id: str
    node_type: str
    label: str
    edge_type: str | None = None
    edge_id: str | None = None
    depth: int = 0
    score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEvidence:
    seed_node_ids: list[str] = field(default_factory=list)
    items: list[GraphEvidenceItem] = field(default_factory=list)
    traversal: dict[str, Any] = field(default_factory=dict)
    contribution_score: float = 0.0
    elapsed_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_node_ids": self.seed_node_ids,
            "items": [item.to_dict() for item in self.items],
            "traversal": self.traversal,
            "contribution_score": self.contribution_score,
            "elapsed_ms": self.elapsed_ms,
            "warnings": self.warnings,
        }


@dataclass
class GraphStatistics:
    node_count: int = 0
    edge_count: int = 0
    nodes_by_type: dict[str, int] = field(default_factory=dict)
    edges_by_type: dict[str, int] = field(default_factory=dict)
    connected_components: int = 0
    average_degree: float = 0.0
    coverage: float = 0.0
    orphan_nodes: list[str] = field(default_factory=list)
    disconnected_nodes: list[str] = field(default_factory=list)
    build_time_ms: float = 0.0
    graph_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphHealth:
    status: str = "healthy"
    cycles_detected: int = 0
    low_confidence_edges: int = 0
    orphan_count: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
