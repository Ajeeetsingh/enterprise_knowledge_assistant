"""Phase 4A — answer planning classification + structure regression (no LLM).

Verifies foundation/governance acceptance questions map to the expected
answer types and blueprints. Does not modify retrieval.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import AnswerType, plan_answer

ACCEPTANCE_CASES: list[tuple[str, AnswerType, str]] = [
    (
        "What is Apex National Bank's mission, vision, and core values?",
        AnswerType.DEFINITION,
        "Definition_v1",
    ),
    (
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        AnswerType.LIST_EXTRACTION,
        "ListExtraction_v1",
    ),
    (
        "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
        AnswerType.RELATIONSHIP,
        "Relationship_v1",
    ),
    (
        "Explain how document identifiers, filenames, and versioning work together.",
        AnswerType.RELATIONSHIP,
        "Relationship_v1",
    ),
    (
        "Describe the complete governance journey.",
        AnswerType.WORKFLOW,
        "Workflow_v1",
    ),
    (
        "Which committee should approve this?",
        AnswerType.DECISION_GUIDANCE,
        "DecisionGuidance_v1",
    ),
    (
        "What is the Records Retention Policy?",
        AnswerType.DEFINITION,
        "Definition_v1",
    ),
    (
        "What Business Process Classification connections must every L3 process declare?",
        AnswerType.LIST_EXTRACTION,
        "ListExtraction_v1",
    ),
]


def main() -> int:
    print("=" * 60)
    print("PHASE 4A — ANSWER PLANNING REGRESSION")
    print("=" * 60)
    failures = 0
    for question, expected_type, expected_blueprint in ACCEPTANCE_CASES:
        plan = plan_answer(question)
        ok = (
            plan.answer_type == expected_type
            and plan.blueprint.blueprint_key == expected_blueprint
        )
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"\n[{status}] {question}")
        print(f"  Question Type: {plan.answer_type.value}")
        print(f"  Planner Decision: {plan.answer_type.value}")
        print(f"  Blueprint Selected: {plan.blueprint.blueprint_key}")
        print(f"  Reason: {plan.reason}")
        print("  Structure:")
        for index, section in enumerate(plan.blueprint.sections, start=1):
            print(f"    {index}. {section}")
        if not ok:
            print(f"  EXPECTED type={expected_type.value} blueprint={expected_blueprint}")

    print("\n" + "=" * 60)
    print(f"RESULT: {len(ACCEPTANCE_CASES) - failures}/{len(ACCEPTANCE_CASES)} passed")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
