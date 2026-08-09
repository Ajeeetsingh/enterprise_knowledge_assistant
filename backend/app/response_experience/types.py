"""ResponseLayout model for Phase 5A/5B (consumed by markdown renderer)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.response_experience.enums import ResponseComponent, ResponseLayoutType


@dataclass(frozen=True)
class ResponseLayout:
    """Presentation plan for one answer — structure only, no rendering."""

    layout: ResponseLayoutType
    components: tuple[ResponseComponent, ...]
    page_structure: tuple[str, ...]
    heading_hierarchy: tuple[str, ...]
    section_order: tuple[str, ...]
    visual_emphasis: str
    expected_render_type: str
    reason: str
    decisions: tuple[str, ...] = ()
    adaptive_flags: tuple[str, ...] = ()
    answer_type: str | None = None
    blueprint_id: str | None = None
    # Deterministic render order (Phase 5B) — higher priority first.
    render_order: tuple[ResponseComponent, ...] = ()
    component_priorities: tuple[tuple[str, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        render_order = [item.value for item in self.render_order] or [
            item.value for item in self.components
        ]
        return {
            "response_layout": self.layout.value,
            "layout": self.layout.value,
            "layout_title": self.layout.value.replace("_", " ").title(),
            "components": [item.value for item in self.components],
            "components_selected": [item.value for item in self.components],
            "page_structure": list(self.page_structure),
            "heading_hierarchy": list(self.heading_hierarchy),
            "section_order": list(self.section_order),
            "render_order": render_order,
            "component_priorities": {
                key: value for key, value in self.component_priorities
            },
            "visual_emphasis": self.visual_emphasis,
            "expected_render_type": self.expected_render_type,
            "layout_decision": self.layout.value,
            "reason": self.reason,
            "decisions": list(self.decisions),
            "adaptive_flags": list(self.adaptive_flags),
            "answer_type": self.answer_type,
            "blueprint_id": self.blueprint_id,
        }
