"""Types for Phase 4A answer planning."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.answer_planning.enums import AnswerType


@dataclass(frozen=True)
class AnswerBlueprint:
    """Ordered section template the LLM should follow."""

    id: str
    answer_type: AnswerType
    title: str
    sections: tuple[str, ...]
    version: str = "v1"

    @property
    def blueprint_key(self) -> str:
        return f"{self.id}_{self.version}"


@dataclass(frozen=True)
class AnswerPlan:
    """Deterministic plan describing HOW to structure the answer (not the answer)."""

    answer_type: AnswerType
    blueprint: AnswerBlueprint
    reason: str
    matched_signals: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "question_type": self.answer_type.value,
            "planner_decision": self.answer_type.value,
            "blueprint_selected": self.blueprint.blueprint_key,
            "blueprint_title": self.blueprint.title,
            "sections": list(self.blueprint.sections),
            "reason": self.reason,
            "matched_signals": list(self.matched_signals),
        }

    def format_for_prompt(self) -> str:
        """Render structure guidance for the prompt builder (no facts)."""
        lines = [
            "Answer planning (structure only — do not invent facts):",
            f"Question type: {self.blueprint.title}",
            f"Blueprint: {self.blueprint.blueprint_key}",
            "Recommended structure:",
        ]
        for index, section in enumerate(self.blueprint.sections, start=1):
            lines.append(f"{index}. {section}")
        lines.append(
            "Follow this structure using ONLY the retrieved excerpts. "
            "Omit any section that has no supporting evidence. "
            "Do not add facts, names, or policies that are absent from the excerpts."
        )
        return "\n".join(lines)
