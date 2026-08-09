"""Evidence graph types for Phase 4B organization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evidence_organization.enums import EvidenceRelationKind, EvidenceStructureKind


@dataclass
class EvidenceNode:
    """One grouped evidence node backed by original retrieved chunks."""

    node_id: str
    label: str
    structure_kind: EvidenceStructureKind
    chunk_ids: list[str]
    source: str
    page_numbers: list[int] = field(default_factory=list)
    hierarchy_path: tuple[str, ...] = ()
    section_title: str | None = None
    # Exact retrieved content blocks — never rewritten.
    evidence_texts: list[str] = field(default_factory=list)
    child_ids: list[str] = field(default_factory=list)
    original_ranks: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "structure_kind": self.structure_kind.value,
            "chunk_ids": list(self.chunk_ids),
            "source": self.source,
            "page_numbers": list(self.page_numbers),
            "hierarchy_path": list(self.hierarchy_path),
            "section_title": self.section_title,
            "child_ids": list(self.child_ids),
            "original_ranks": list(self.original_ranks),
            "evidence_preview": [
                (text[:240] + "…") if len(text) > 240 else text
                for text in self.evidence_texts
            ],
        }


@dataclass(frozen=True)
class EvidenceLink:
    """Directed structural link between nodes."""

    from_node_id: str
    to_node_id: str
    relation: EvidenceRelationKind
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_node_id,
            "to": self.to_node_id,
            "relation": self.relation.value,
            "reason": self.reason,
        }


@dataclass
class EvidenceGraph:
    """Ordered evidence graph built only from retrieved chunks."""

    nodes: list[EvidenceNode] = field(default_factory=list)
    links: list[EvidenceLink] = field(default_factory=list)
    ordering_decisions: list[str] = field(default_factory=list)
    structure_profile: str = "section"
    answer_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "structure_profile": self.structure_profile,
            "answer_type": self.answer_type,
            "ordering_decisions": list(self.ordering_decisions),
            "nodes": [node.to_dict() for node in self.nodes],
            "links": [link.to_dict() for link in self.links],
            "node_count": len(self.nodes),
            "chunk_ids": [
                chunk_id for node in self.nodes for chunk_id in node.chunk_ids
            ],
        }

    def format_for_prompt(self) -> str:
        """Render organized evidence for the LLM (original text only)."""
        if not self.nodes:
            return (
                "Organized evidence graph:\n"
                "(No document excerpts retrieved.)"
            )

        lines: list[str] = [
            "Organized evidence graph "
            "(retrieved excerpts reorganized only — no new facts):",
            f"Structure profile: {self.structure_profile}",
        ]
        if self.answer_type:
            lines.append(f"Aligned answer type: {self.answer_type}")
        lines.append("")

        for index, node in enumerate(self.nodes, start=1):
            pages = (
                ", ".join(str(p) for p in node.page_numbers)
                if node.page_numbers
                else "unknown"
            )
            lines.append(f"[Group {index}] {node.label}")
            lines.append(f"  structure: {node.structure_kind.value}")
            lines.append(f"  source: {node.source}")
            lines.append(f"  pages: {pages}")
            lines.append(f"  chunk_ids: {', '.join(node.chunk_ids)}")
            if node.hierarchy_path:
                lines.append(f"  hierarchy: {' > '.join(node.hierarchy_path)}")
            if node.child_ids:
                lines.append(f"  children: {', '.join(node.child_ids)}")
            lines.append("  Evidence:")
            for text in node.evidence_texts:
                cleaned = text.strip()
                if not cleaned:
                    continue
                lines.append("  ---")
                lines.append(cleaned)
                lines.append("  ---")
            lines.append("")

        if self.links:
            lines.append("Evidence links:")
            for link in self.links:
                lines.append(
                    f"  {link.from_node_id} -> {link.to_node_id} "
                    f"({link.relation.value}; {link.reason})"
                )
            lines.append("")

        lines.append(
            "Use this graph for ordering and grouping only. "
            "Every factual claim must come from the Evidence blocks above."
        )
        return "\n".join(lines)
