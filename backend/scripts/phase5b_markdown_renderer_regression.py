"""Phase 5B — Enterprise Markdown Renderer regression."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.response_experience import (
    content_preserved,
    plan_response_experience,
    render_enterprise_markdown,
)

CASES: list[tuple[str, str, str]] = [
    (
        "What is Apex National Bank's mission, vision, and core values?",
        "definition",
        (
            "Apex National Bank's mission is to steward clients' financial lives. "
            "Its vision is to be the most trusted and operationally resilient bank. "
            "Core values include Integrity First, Client Stewardship, and Accountability."
        ),
    ),
    (
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        "list_extraction",
        (
            "The metadata categories include Administrative Metadata, Business Metadata, "
            "Technical Metadata, and Compliance Metadata."
        ),
    ),
    (
        "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
        "hierarchy",
        "L1: Domain\nL2: Category\nL3: Sub-category\nL4: Document Type\n"
        "The hierarchy supports faceted enterprise search and consistent classification.",
    ),
    (
        "What are the approval rules in the Approval Authority Matrix?",
        "decision_guidance",
        (
            "Approval authority is determined by document class and risk. "
            "Routine changes follow delegated authority; material changes escalate "
            "to the named committee in the matrix."
        ),
    ),
    (
        "Describe the complete governance journey.",
        "workflow",
        (
            "The objective is controlled document handling across the enterprise.\n\n"
            "1. Creation and metadata capture\n"
            "2. Naming and classification\n"
            "3. Approval\n"
            "4. Publication\n"
            "5. Retention and archival\n\n"
            "Roles include authors, approvers, and records owners. "
            "The outcome is durable, searchable governance."
        ),
    ),
    (
        "Which committee should approve this?",
        "decision_guidance",
        (
            "The Enterprise Risk Committee should approve material risk-policy changes. "
            "Escalate to the Board Risk Committee when thresholds in the charter are met."
        ),
    ),
    (
        "You are the Head of Enterprise Knowledge Management. Write a 500-word overview.",
        "executive_report",
        (
            "Enterprise knowledge management connects metadata, taxonomy, naming, "
            "approval, and retention into one operating system for documents.\n\n"
            "Metadata standards define required fields at creation. "
            "Taxonomy provides the hierarchy for search. "
            "Naming and versioning keep identifiers stable. "
            "Approval matrices and committee charters establish authority. "
            "Retention policies close the lifecycle with defensible archival rules.\n\n"
            "Together these standards reduce ambiguity, improve retrieval quality, "
            "and give leaders a single accountable model for enterprise knowledge."
        ),
    ),
]


def _relative_order_preserved(expected: list[str], actual: list[str]) -> bool:
    positions = {item: index for index, item in enumerate(actual)}
    last = -1
    for item in expected:
        if item not in positions:
            continue
        if positions[item] < last:
            return False
        last = positions[item]
    return True


def main() -> int:
    print("=" * 60)
    print("PHASE 5B — ENTERPRISE MARKDOWN RENDERER REGRESSION")
    print("=" * 60)
    failures = 0
    for question, expected_layout, answer in CASES:
        plan = plan_answer(question)
        layout = plan_response_experience(
            question=question,
            answer=answer,
            answer_plan=plan,
        )
        result = render_enterprise_markdown(
            layout=layout,
            answer=answer,
            question=question,
            sources=["EXAMPLE_SOURCE.pdf"],
        )
        checks = {
            "layout": layout.layout.value == expected_layout,
            "render_order": bool(layout.render_order),
            "has_title": result.markdown.startswith("# "),
            "has_sources": "## Sources" in result.markdown,
            "content_preserved": content_preserved(answer, result.markdown),
            "template": bool(result.template_used),
            # Phase 5C may add adaptive components; relative 5B order must hold.
            "order_from_layout": _relative_order_preserved(
                [item.value for item in layout.render_order],
                result.render_order,
            ),
        }
        ok = all(checks.values())
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"\n[{status}] {question[:72]}")
        print(f"  Layout: {layout.layout.value} (expected {expected_layout})")
        print(f"  Template: {result.template_used}")
        print(f"  Rendered components: {result.components_rendered}")
        print(f"  Skipped: {result.components_skipped}")
        if not ok:
            print(f"  Failed checks: {[k for k, v in checks.items() if not v]}")

    print("\n" + "=" * 60)
    print(f"RESULT: {len(CASES) - failures}/{len(CASES)} passed")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
