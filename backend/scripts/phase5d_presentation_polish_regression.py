"""Phase 5D — presentation polish regression."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.response_experience import (
    content_preserved,
    plan_response_experience,
    polish_enterprise_markdown,
    render_enterprise_markdown,
)

CASES = [
    (
        "What is Apex National Bank's mission, vision, and core values?",
        (
            "Apex National Bank's mission is to steward clients' financial lives. "
            "Its vision is to be the most trusted and operationally resilient bank. "
            "Core values include Integrity First, Client Stewardship, and Accountability."
        ),
    ),
    (
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        (
            "The metadata categories include Administrative Metadata, Business Metadata, "
            "Technical Metadata, and Compliance Metadata."
        ),
    ),
    (
        "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
        "L1: Domain\nL2: Category\nL3: Sub-category\nL4: Document Type\n"
        "The hierarchy supports faceted enterprise search.",
    ),
    (
        "Describe the complete governance journey.",
        (
            "The objective is controlled document handling.\n\n"
            "1. Create\n2. Review\n3. Approve\n4. Publish\n5. Retain\n6. Archive\n\n"
            "Roles include authors and approvers."
        ),
    ),
    (
        "Which committee should approve this?",
        (
            "The Enterprise Risk Committee should approve material risk-policy changes. "
            "Escalate to the Board Risk Committee when thresholds in the charter are met."
        ),
    ),
]


def main() -> int:
    print("=" * 60)
    print("PHASE 5D — PRESENTATION POLISH REGRESSION")
    print("=" * 60)
    failures = 0
    for question, answer in CASES:
        plan = plan_answer(question)
        layout = plan_response_experience(
            question=question, answer=answer, answer_plan=plan
        )
        rendered = render_enterprise_markdown(
            layout=layout,
            answer=answer,
            question=question,
            sources=["EXAMPLE.pdf"],
        )
        polished = polish_enterprise_markdown(rendered.markdown)
        checks = {
            "content_preserved": content_preserved(answer, polished.markdown),
            "has_title": polished.markdown.startswith("# "),
            "no_h4": "#### " not in polished.markdown,
            "has_sources": "## Sources" in polished.markdown,
            "transforms_reported": isinstance(polished.transforms_applied, list),
        }
        ok = all(checks.values())
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"\n[{status}] {question[:72]}")
        print(f"  Layout: {layout.layout.value}")
        print(f"  Transforms: {polished.transforms_applied}")
        if not ok:
            print(f"  Failed: {[k for k, v in checks.items() if not v]}")

    print("\n" + "=" * 60)
    print(f"RESULT: {len(CASES) - failures}/{len(CASES)} passed")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
