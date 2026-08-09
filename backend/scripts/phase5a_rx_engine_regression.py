"""Phase 5A — Response Experience Engine regression (no rendering / no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.answer_synthesis import plan_answer_synthesis
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.response_experience import plan_response_experience
from app.rag.types import RetrievalResult


CASES: list[tuple[str, str]] = [
    (
        "What is Apex National Bank's mission, vision, and core values?",
        "definition",
    ),
    (
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        "list_extraction",
    ),
    (
        "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
        "hierarchy",
    ),
    (
        "What are the approval rules in the Approval Authority Matrix?",
        "decision_guidance",
    ),
    (
        "Describe the complete governance journey.",
        "workflow",
    ),
    (
        "Which committee should approve this?",
        "decision_guidance",
    ),
    (
        "You are the Head of Enterprise Knowledge Management. Write a 500-word overview of how knowledge standards work together.",
        "executive_report",
    ),
]


def main() -> int:
    print("=" * 60)
    print("PHASE 5A — RESPONSE EXPERIENCE ENGINE REGRESSION")
    print("=" * 60)
    failures = 0
    for question, expected in CASES:
        plan = plan_answer(question)
        graph = organize_evidence([], answer_plan=plan)
        composition = compose_answer_evidence(graph, question=question, answer_plan=plan)
        synthesis = plan_answer_synthesis(
            question=question,
            answer_plan=plan,
            evidence_graph=graph,
            answer_composition=composition,
        )
        layout = plan_response_experience(
            question=question,
            answer="Synthetic answer for layout planning only.",
            answer_plan=plan,
            evidence_graph=graph,
            answer_synthesis=synthesis,
        )
        ok = layout.layout.value == expected
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"\n[{status}] {question}")
        print(f"  Expected layout: {expected}")
        print(f"  Selected layout: {layout.layout.value}")
        print(f"  Components: {[c.value for c in layout.components]}")
        print(f"  Expected render type: {layout.expected_render_type}")
        print(f"  Reason: {layout.reason}")
        if not ok:
            print(f"  Decisions: {list(layout.decisions)}")

    print("\n" + "=" * 60)
    print(f"RESULT: {len(CASES) - failures}/{len(CASES)} passed")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
