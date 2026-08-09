"""Predefined answer blueprints for each answer type."""

from __future__ import annotations

from app.answer_planning.enums import AnswerType
from app.answer_planning.types import AnswerBlueprint

_BLUEPRINTS: dict[AnswerType, AnswerBlueprint] = {
    AnswerType.DEFINITION: AnswerBlueprint(
        id="Definition",
        answer_type=AnswerType.DEFINITION,
        title="Definition",
        version="v1",
        sections=(
            "Short definition",
            "Purpose",
            "Key characteristics",
            "Important notes",
        ),
    ),
    AnswerType.EXPLANATION: AnswerBlueprint(
        id="Explanation",
        answer_type=AnswerType.EXPLANATION,
        title="Explanation",
        version="v1",
        sections=(
            "Overview",
            "How it works",
            "Key components",
            "Practical implications",
        ),
    ),
    AnswerType.RELATIONSHIP: AnswerBlueprint(
        id="Relationship",
        answer_type=AnswerType.RELATIONSHIP,
        title="Relationship",
        version="v1",
        sections=(
            "Introduce the concepts",
            "Explain each concept",
            "Explain how they relate",
            "Business significance",
        ),
    ),
    AnswerType.COMPARISON: AnswerBlueprint(
        id="Comparison",
        answer_type=AnswerType.COMPARISON,
        title="Comparison",
        version="v1",
        sections=(
            "Entities being compared",
            "Key differences",
            "Key similarities",
            "When each applies",
        ),
    ),
    AnswerType.WORKFLOW: AnswerBlueprint(
        id="Workflow",
        answer_type=AnswerType.WORKFLOW,
        title="Workflow",
        version="v1",
        sections=(
            "Objective",
            "Ordered steps",
            "Roles and responsibilities",
            "Outcome",
        ),
    ),
    AnswerType.POLICY_LOOKUP: AnswerBlueprint(
        id="Policy",
        answer_type=AnswerType.POLICY_LOOKUP,
        title="Policy Lookup",
        version="v1",
        sections=(
            "Purpose",
            "Scope",
            "Requirements",
            "Exceptions",
            "Governance",
        ),
    ),
    AnswerType.GOVERNANCE: AnswerBlueprint(
        id="Governance",
        answer_type=AnswerType.GOVERNANCE,
        title="Governance",
        version="v1",
        sections=(
            "Governance context",
            "Bodies and roles",
            "Authorities and mandates",
            "Escalation or oversight",
        ),
    ),
    AnswerType.DECISION_GUIDANCE: AnswerBlueprint(
        id="DecisionGuidance",
        answer_type=AnswerType.DECISION_GUIDANCE,
        title="Decision Guidance",
        version="v1",
        sections=(
            "Decision to be made",
            "Applicable criteria",
            "Recommended authority or path",
            "Constraints and notes",
        ),
    ),
    AnswerType.TROUBLESHOOTING: AnswerBlueprint(
        id="Troubleshooting",
        answer_type=AnswerType.TROUBLESHOOTING,
        title="Troubleshooting",
        version="v1",
        sections=(
            "Problem summary",
            "Likely causes from the evidence",
            "Recommended checks or actions",
            "Escalation or follow-up",
        ),
    ),
    AnswerType.SUMMARY: AnswerBlueprint(
        id="Summary",
        answer_type=AnswerType.SUMMARY,
        title="Summary",
        version="v1",
        sections=(
            "High-level summary",
            "Key points",
            "Supporting details",
        ),
    ),
    AnswerType.COMPLIANCE: AnswerBlueprint(
        id="Compliance",
        answer_type=AnswerType.COMPLIANCE,
        title="Compliance",
        version="v1",
        sections=(
            "Obligation or requirement",
            "Who it applies to",
            "Controls or evidence expected",
            "Consequences or related governance",
        ),
    ),
    AnswerType.LIST_EXTRACTION: AnswerBlueprint(
        id="ListExtraction",
        answer_type=AnswerType.LIST_EXTRACTION,
        title="List Extraction",
        version="v1",
        sections=(
            "Direct answer list",
            "Brief description of each item",
            "Source context notes",
        ),
    ),
    AnswerType.REFERENCE_LOOKUP: AnswerBlueprint(
        id="ReferenceLookup",
        answer_type=AnswerType.REFERENCE_LOOKUP,
        title="Reference Lookup",
        version="v1",
        sections=(
            "Direct reference answer",
            "Where it appears",
            "Related identifiers or pointers",
        ),
    ),
}


def get_blueprint(answer_type: AnswerType) -> AnswerBlueprint:
    """Return the blueprint for an answer type (always defined)."""
    return _BLUEPRINTS[answer_type]


def all_blueprints() -> dict[AnswerType, AnswerBlueprint]:
    """Return a copy of the blueprint catalog."""
    return dict(_BLUEPRINTS)
