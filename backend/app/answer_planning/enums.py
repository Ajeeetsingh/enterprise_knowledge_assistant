"""Answer-structure question types (Phase 4A).

Separate from retrieval ``QueryCategory`` — these control answer layout only.
"""

from __future__ import annotations

from enum import Enum


class AnswerType(str, Enum):
    """Primary answer-structure intent for prompt planning."""

    DEFINITION = "definition"
    EXPLANATION = "explanation"
    RELATIONSHIP = "relationship"
    COMPARISON = "comparison"
    WORKFLOW = "workflow"
    POLICY_LOOKUP = "policy_lookup"
    GOVERNANCE = "governance"
    DECISION_GUIDANCE = "decision_guidance"
    TROUBLESHOOTING = "troubleshooting"
    SUMMARY = "summary"
    COMPLIANCE = "compliance"
    LIST_EXTRACTION = "list_extraction"
    REFERENCE_LOOKUP = "reference_lookup"
