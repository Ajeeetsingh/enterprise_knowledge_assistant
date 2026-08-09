"""Lightweight graph metrics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphMetrics:
    builds: int = 0
    traversals: int = 0
    expansions: int = 0
    total_build_ms: float = 0.0
    total_traversal_ms: float = 0.0
    total_expansion_ms: float = 0.0

    def record_build(self, elapsed_ms: float) -> None:
        self.builds += 1
        self.total_build_ms += elapsed_ms

    def record_traversal(self, elapsed_ms: float) -> None:
        self.traversals += 1
        self.total_traversal_ms += elapsed_ms

    def record_expansion(self, elapsed_ms: float) -> None:
        self.expansions += 1
        self.total_expansion_ms += elapsed_ms

    def to_dict(self) -> dict:
        return {
            "builds": self.builds,
            "traversals": self.traversals,
            "expansions": self.expansions,
            "average_build_ms": round(self.total_build_ms / self.builds, 4) if self.builds else 0.0,
            "average_traversal_ms": (
                round(self.total_traversal_ms / self.traversals, 4) if self.traversals else 0.0
            ),
            "average_expansion_ms": (
                round(self.total_expansion_ms / self.expansions, 4) if self.expansions else 0.0
            ),
        }
