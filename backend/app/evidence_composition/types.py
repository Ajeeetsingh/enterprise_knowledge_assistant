"""Answer composition types for Phase 4C."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.evidence_composition.enums import EvidencePriority
from app.evidence_organization.types import EvidenceNode


@dataclass
class PrioritizedEvidence:
    """One evidence group with a deterministic priority assignment."""

    node: EvidenceNode
    priority: EvidencePriority
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node.node_id,
            "label": self.node.label,
            "priority": self.priority.value,
            "score": round(self.score, 4),
            "reasons": list(self.reasons),
            "chunk_ids": list(self.node.chunk_ids),
            "structure_kind": self.node.structure_kind.value,
            "source": self.node.source,
        }


@dataclass
class AnswerComposition:
    """Prioritized view of organized evidence for prompting."""

    primary: list[PrioritizedEvidence] = field(default_factory=list)
    supporting: list[PrioritizedEvidence] = field(default_factory=list)
    optional: list[PrioritizedEvidence] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    answer_type: str | None = None
    structure_profile: str | None = None

    @property
    def all_items(self) -> list[PrioritizedEvidence]:
        return [*self.primary, *self.supporting, *self.optional]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_type": self.answer_type,
            "structure_profile": self.structure_profile,
            "decisions": list(self.decisions),
            "priority_scores": [
                {
                    "label": item.node.label,
                    "priority": item.priority.value,
                    "score": round(item.score, 4),
                    "reasons": list(item.reasons),
                    "chunk_ids": list(item.node.chunk_ids),
                }
                for item in self.all_items
            ],
            "primary_evidence": [item.to_dict() for item in self.primary],
            "supporting_evidence": [item.to_dict() for item in self.supporting],
            "optional_evidence": [item.to_dict() for item in self.optional],
            "final_composition": {
                "primary": [item.node.label for item in self.primary],
                "supporting": [item.node.label for item in self.supporting],
                "optional": [item.node.label for item in self.optional],
            },
        }

    def format_for_prompt(self) -> str:
        """Render prioritized evidence for the LLM (original texts only)."""
        if not self.all_items:
            return "Answer composition:\n(No document excerpts retrieved.)"

        lines: list[str] = [
            "Answer composition "
            "(priority guidance — factual content only from Evidence blocks below):",
        ]
        if self.answer_type:
            lines.append(f"Answer type: {self.answer_type}")
        if self.structure_profile:
            lines.append(f"Structure profile: {self.structure_profile}")
        lines.append(
            "Focus the answer on PRIMARY evidence. "
            "Use SUPPORTING evidence to enrich. "
            "Use OPTIONAL context only when it materially helps."
        )
        lines.append("")

        self._emit_tier(
            lines,
            "PRIMARY EVIDENCE",
            "Focus most of the answer here.",
            self.primary,
        )
        self._emit_tier(
            lines,
            "SUPPORTING EVIDENCE",
            "Enrich the answer when relevant.",
            self.supporting,
        )
        self._emit_tier(
            lines,
            "OPTIONAL CONTEXT",
            "Use only if helpful; do not let this dominate.",
            self.optional,
        )
        lines.append(
            "Every factual claim must come from the Evidence blocks above. "
            "Do not invent facts to fill the answer blueprint."
        )
        return "\n".join(lines)

    @staticmethod
    def _emit_tier(
        lines: list[str],
        tier_name: str,
        guidance: str,
        items: list[PrioritizedEvidence],
    ) -> None:
        lines.append(f"=== {tier_name} ===")
        lines.append(guidance)
        if not items:
            lines.append("(none)")
            lines.append("")
            return
        prefix = tier_name.split()[0]
        for index, item in enumerate(items, start=1):
            node = item.node
            pages = (
                ", ".join(str(p) for p in node.page_numbers)
                if node.page_numbers
                else "unknown"
            )
            lines.append(f"[{prefix} {index}] {node.label}")
            lines.append(f"  priority_score: {item.score:.3f}")
            lines.append(f"  structure: {node.structure_kind.value}")
            lines.append(f"  source: {node.source}")
            lines.append(f"  pages: {pages}")
            lines.append(f"  chunk_ids: {', '.join(node.chunk_ids)}")
            if item.reasons:
                lines.append(f"  why: {'; '.join(item.reasons[:3])}")
            lines.append("  Evidence:")
            for text in node.evidence_texts:
                cleaned = text.strip()
                if not cleaned:
                    continue
                lines.append("  ---")
                lines.append(cleaned)
                lines.append("  ---")
            lines.append("")
