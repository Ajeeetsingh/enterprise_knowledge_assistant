"""Deterministic layout selection for the RX Engine (Phase 5A)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from app.response_experience.enums import ResponseComponent, ResponseLayoutType
from app.response_experience.layouts import get_layout_definition
from app.response_experience.ordering import compute_render_order, priorities_for
from app.response_experience.types import ResponseLayout

if TYPE_CHECKING:
    from app.answer_planning.types import AnswerPlan
    from app.answer_synthesis.types import SynthesisPlan
    from app.evidence_organization.types import EvidenceGraph

_ANSWER_TYPE_TO_LAYOUT: dict[str, ResponseLayoutType] = {
    "definition": ResponseLayoutType.DEFINITION,
    "explanation": ResponseLayoutType.MIXED,
    "relationship": ResponseLayoutType.RELATIONSHIP,
    "comparison": ResponseLayoutType.COMPARISON,
    "workflow": ResponseLayoutType.WORKFLOW,
    "policy_lookup": ResponseLayoutType.POLICY,
    "governance": ResponseLayoutType.GOVERNANCE,
    "decision_guidance": ResponseLayoutType.DECISION_GUIDANCE,
    "troubleshooting": ResponseLayoutType.TROUBLESHOOTING,
    "summary": ResponseLayoutType.EXECUTIVE_SUMMARY,
    "compliance": ResponseLayoutType.COMPLIANCE,
    "list_extraction": ResponseLayoutType.LIST_EXTRACTION,
    "reference_lookup": ResponseLayoutType.REFERENCE_LOOKUP,
}

_HIERARCHY_RE = re.compile(
    r"\b(taxonomy|hierarchy|levels?|l[1-4]\b|tree structure)\b",
    re.I,
)
_EXECUTIVE_RE = re.compile(
    r"\b("
    r"head of|you are the|500[- ]word|executive (?:brief|summary|report)|"
    r"enterprise knowledge management"
    r")\b",
    re.I,
)
_TIMELINE_RE = re.compile(
    r"\b(timeline|chronolog|milestones?|sequence of events)\b",
    re.I,
)
_TABLE_RE = re.compile(
    r"\b(table|matrix|compare in a table|tabular)\b",
    re.I,
)
_APPROVAL_RE = re.compile(
    r"\b(approval (?:authority|matrix|rules?|path)|who (?:should|must) approve|"
    r"which committee|should approve)\b",
    re.I,
)
_POLICY_TITLE_RE = re.compile(
    r"\b(retention policy|records retention|policy)\b",
    re.I,
)
_LONG_REPORT_RE = re.compile(
    r"\b(detailed report|comprehensive|in depth|long[- ]form)\b",
    re.I,
)


def _answer_len(answer: str | None) -> int:
    return len((answer or "").strip())


def _question_len(question: str | None) -> int:
    return len((question or "").strip())


def _structure_profile(graph: EvidenceGraph | None) -> str | None:
    if graph is None:
        return None
    return getattr(graph, "structure_profile", None)


def _synthesis_mode(synthesis: SynthesisPlan | None) -> str | None:
    if synthesis is None:
        return None
    return getattr(synthesis, "mode", None)


def select_layout_type(
    *,
    question: str,
    answer_plan: AnswerPlan | None,
    evidence_graph: EvidenceGraph | None = None,
    answer_synthesis: SynthesisPlan | None = None,
    answer: str | None = None,
) -> tuple[ResponseLayoutType, list[str]]:
    """Choose a layout type and collect decision reasons."""
    decisions: list[str] = []
    q = question or ""

    # Strong presentation overrides (deterministic, question-shaped).
    if _EXECUTIVE_RE.search(q) or _synthesis_mode(answer_synthesis) == "executive":
        decisions.append("override=executive_report")
        return ResponseLayoutType.EXECUTIVE_REPORT, decisions

    if _HIERARCHY_RE.search(q):
        decisions.append("override=hierarchy_from_question")
        return ResponseLayoutType.HIERARCHY, decisions

    if _APPROVAL_RE.search(q):
        decisions.append("override=decision_guidance_from_approval")
        return ResponseLayoutType.DECISION_GUIDANCE, decisions

    if _TIMELINE_RE.search(q):
        decisions.append("override=timeline")
        return ResponseLayoutType.TIMELINE, decisions

    if _TABLE_RE.search(q):
        decisions.append("override=table_heavy")
        return ResponseLayoutType.TABLE_HEAVY, decisions

    if _LONG_REPORT_RE.search(q) and _question_len(q) > 120:
        decisions.append("override=long_report")
        return ResponseLayoutType.LONG_REPORT, decisions

    profile = _structure_profile(evidence_graph)
    if profile == "taxonomy":
        decisions.append("override=hierarchy_from_evidence_profile")
        return ResponseLayoutType.HIERARCHY, decisions
    if profile == "workflow":
        decisions.append("hint=workflow_profile")
    if profile == "approval_flow":
        decisions.append("override=decision_from_approval_profile")
        return ResponseLayoutType.DECISION_GUIDANCE, decisions

    answer_type = None
    if answer_plan is not None:
        answer_type = answer_plan.answer_type.value
        decisions.append(f"answer_type={answer_type}")
        # Policy title questions often classify as definition — present as policy.
        if answer_type == "definition" and _POLICY_TITLE_RE.search(q):
            if re.search(r"\b(retention|records|policy)\b", q, re.I) and re.search(
                r"\bwhat is\b", q, re.I
            ):
                # Keep definition for mission-style; only force policy when clearly a policy doc ask
                # with policy/requirements framing beyond "what is X policy" short title.
                if re.search(r"\b(require|scope|exception|applies|shall|must)\b", q, re.I):
                    decisions.append("override=policy_from_requirements_language")
                    return ResponseLayoutType.POLICY, decisions

        mapped = _ANSWER_TYPE_TO_LAYOUT.get(answer_type)
        if mapped is not None:
            # Relationship + taxonomy already handled; workflow stays workflow.
            if mapped == ResponseLayoutType.RELATIONSHIP and _HIERARCHY_RE.search(q):
                decisions.append("remap=relationship_to_hierarchy")
                return ResponseLayoutType.HIERARCHY, decisions
            decisions.append(f"mapped_from_answer_type={mapped.value}")
            return mapped, decisions

    # Fallback heuristics.
    if _answer_len(answer) > 1800:
        decisions.append("fallback=long_report_from_answer_length")
        return ResponseLayoutType.LONG_REPORT, decisions

    decisions.append("fallback=mixed")
    return ResponseLayoutType.MIXED, decisions


def adapt_components(
    *,
    layout_type: ResponseLayoutType,
    preferred: tuple[ResponseComponent, ...],
    question: str,
    answer: str | None,
) -> tuple[tuple[ResponseComponent, ...], tuple[str, ...]]:
    """Adapt component set for short/long answers without changing layout type."""
    flags: list[str] = []
    components = list(preferred)
    q_len = _question_len(question)
    a_len = _answer_len(answer)

    def drop(component: ResponseComponent, flag: str) -> None:
        if component in components:
            components.remove(component)
            flags.append(flag)

    def ensure(component: ResponseComponent, flag: str) -> None:
        if component not in components:
            # Insert after title when possible.
            if ResponseComponent.TITLE in components:
                idx = components.index(ResponseComponent.TITLE) + 1
                components.insert(idx, component)
            else:
                components.insert(0, component)
            flags.append(flag)

    # Short definition / short answers: no executive summary.
    if layout_type == ResponseLayoutType.DEFINITION and a_len < 500 and q_len < 140:
        drop(ResponseComponent.EXECUTIVE_SUMMARY, "adaptive=omit_exec_summary_short_definition")

    if a_len < 280 and layout_type not in {
        ResponseLayoutType.EXECUTIVE_REPORT,
        ResponseLayoutType.LONG_REPORT,
        ResponseLayoutType.EXECUTIVE_SUMMARY,
    }:
        drop(ResponseComponent.EXECUTIVE_SUMMARY, "adaptive=omit_exec_summary_short_answer")
        drop(ResponseComponent.KEY_TAKEAWAYS, "adaptive=omit_takeaways_short_answer")

    # Long / executive: ensure summary + takeaways + details.
    if layout_type in {
        ResponseLayoutType.EXECUTIVE_REPORT,
        ResponseLayoutType.LONG_REPORT,
    } or a_len > 1200:
        ensure(ResponseComponent.EXECUTIVE_SUMMARY, "adaptive=ensure_exec_summary_long")
        ensure(ResponseComponent.KEY_TAKEAWAYS, "adaptive=ensure_takeaways_long")
        ensure(ResponseComponent.DETAILED_SECTIONS, "adaptive=ensure_details_long")

    if layout_type == ResponseLayoutType.COMPARISON:
        ensure(ResponseComponent.COMPARISON_TABLE, "adaptive=ensure_comparison_table")

    if layout_type == ResponseLayoutType.HIERARCHY:
        ensure(ResponseComponent.HIERARCHY_TREE, "adaptive=ensure_hierarchy_tree")

    if layout_type in {ResponseLayoutType.WORKFLOW, ResponseLayoutType.TIMELINE}:
        ensure(ResponseComponent.TIMELINE, "adaptive=ensure_timeline")

    if layout_type == ResponseLayoutType.POLICY:
        ensure(ResponseComponent.REQUIREMENTS, "adaptive=ensure_policy_requirements")
        ensure(ResponseComponent.EXCEPTIONS, "adaptive=ensure_policy_exceptions")
        ensure(ResponseComponent.OWNER, "adaptive=ensure_policy_owner")
        ensure(ResponseComponent.REVIEW_CYCLE, "adaptive=ensure_policy_review_cycle")

    # Always keep sources last.
    if ResponseComponent.SOURCES in components:
        components = [c for c in components if c != ResponseComponent.SOURCES]
        components.append(ResponseComponent.SOURCES)
    else:
        components.append(ResponseComponent.SOURCES)
        flags.append("adaptive=ensure_sources")

    return tuple(components), tuple(flags)


def build_response_layout(
    *,
    question: str,
    answer: str | None = None,
    answer_plan: AnswerPlan | None = None,
    evidence_graph: EvidenceGraph | None = None,
    answer_synthesis: SynthesisPlan | None = None,
    extra_context: dict[str, Any] | None = None,
) -> ResponseLayout:
    """Build the full ResponseLayout presentation plan."""
    del extra_context  # reserved for future diagnostics-only hints
    layout_type, decisions = select_layout_type(
        question=question,
        answer_plan=answer_plan,
        evidence_graph=evidence_graph,
        answer_synthesis=answer_synthesis,
        answer=answer,
    )
    definition = get_layout_definition(layout_type)
    components, adaptive_flags = adapt_components(
        layout_type=layout_type,
        preferred=definition.preferred_components,
        question=question,
        answer=answer,
    )

    answer_type = answer_plan.answer_type.value if answer_plan is not None else None
    blueprint_id = (
        answer_plan.blueprint.blueprint_key if answer_plan is not None else None
    )
    reason = (
        f"Selected {layout_type.value} layout from answer_type={answer_type}, "
        f"blueprint={blueprint_id}, synthesis_mode={_synthesis_mode(answer_synthesis)}, "
        f"structure_profile={_structure_profile(evidence_graph)}"
    )
    render_order = compute_render_order(components)
    priority_map = priorities_for(render_order)
    decisions = list(decisions) + [
        f"components={len(components)}",
        f"render_order={[item.value for item in render_order]}",
    ]

    return ResponseLayout(
        layout=layout_type,
        components=components,
        page_structure=definition.page_structure,
        heading_hierarchy=definition.heading_hierarchy,
        section_order=definition.section_order,
        visual_emphasis=definition.visual_emphasis,
        expected_render_type=definition.expected_render_type,
        reason=reason,
        decisions=tuple(decisions),
        adaptive_flags=adaptive_flags,
        answer_type=answer_type,
        blueprint_id=blueprint_id,
        render_order=render_order,
        component_priorities=tuple(priority_map.items()),
    )
