"""Deterministic component render priorities for ResponseLayout (Phase 5B prep).

Phase 5A provided ``section_order`` and a component tuple, but no numeric
render priority. This module is the single source of truth for render order.
The markdown renderer must never invent ordering.
"""

from __future__ import annotations

from app.response_experience.enums import ResponseComponent

# Higher priority renders earlier. Gaps allow future insertions.
COMPONENT_RENDER_PRIORITY: dict[ResponseComponent, int] = {
    ResponseComponent.TITLE: 110,
    ResponseComponent.EXECUTIVE_SUMMARY: 100,
    # Main sections
    ResponseComponent.DEFINITION: 90,
    ResponseComponent.OBJECTIVE: 90,
    ResponseComponent.PURPOSE: 90,
    ResponseComponent.SCOPE: 90,
    ResponseComponent.DIRECT_LIST: 90,
    ResponseComponent.DETAILED_SECTIONS: 90,
    ResponseComponent.INFORMATION: 90,
    ResponseComponent.DECISION_MATRIX: 90,
    ResponseComponent.RELATIONSHIP_DIAGRAM: 90,
    ResponseComponent.GOVERNANCE: 90,
    # Workflow / process
    ResponseComponent.TIMELINE: 85,
    ResponseComponent.STEPS: 85,
    ResponseComponent.CHECKLIST: 85,
    # Comparison / structured
    ResponseComponent.COMPARISON_TABLE: 80,
    ResponseComponent.KEY_DIFFERENCES: 78,
    ResponseComponent.HIERARCHY_TREE: 75,
    ResponseComponent.KEY_CHARACTERISTICS: 74,
    ResponseComponent.REQUIREMENTS: 74,
    ResponseComponent.EXCEPTIONS: 73,
    ResponseComponent.RESPONSIBILITIES: 72,
    ResponseComponent.OUTCOME: 71,
    ResponseComponent.IMPORTANT_NOTES: 70,
    ResponseComponent.WARNING: 70,
    ResponseComponent.OWNER: 68,
    ResponseComponent.REVIEW_CYCLE: 67,
    ResponseComponent.KEY_TAKEAWAYS: 65,
    ResponseComponent.RECOMMENDATIONS: 64,
    ResponseComponent.RELATED_DOCUMENTS: 60,
    ResponseComponent.RELATED_STANDARDS: 60,
    ResponseComponent.RELATED_POLICIES: 60,
    ResponseComponent.FREQUENTLY_REFERENCED_POLICIES: 58,
    ResponseComponent.SOURCES: 50,
}

_DEFAULT_PRIORITY = 55


def component_priority(component: ResponseComponent) -> int:
    return COMPONENT_RENDER_PRIORITY.get(component, _DEFAULT_PRIORITY)


def compute_render_order(
    components: tuple[ResponseComponent, ...] | list[ResponseComponent],
) -> tuple[ResponseComponent, ...]:
    """Stable sort: higher priority first; original order breaks ties."""
    indexed = list(enumerate(components))
    indexed.sort(key=lambda pair: (-component_priority(pair[1]), pair[0]))
    # Deduplicate while preserving sorted order.
    seen: set[ResponseComponent] = set()
    ordered: list[ResponseComponent] = []
    for _, component in indexed:
        if component in seen:
            continue
        seen.add(component)
        ordered.append(component)
    return tuple(ordered)


def priorities_for(
    components: tuple[ResponseComponent, ...] | list[ResponseComponent],
) -> dict[str, int]:
    return {component.value: component_priority(component) for component in components}
