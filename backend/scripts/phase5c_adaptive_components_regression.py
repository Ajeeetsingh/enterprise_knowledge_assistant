"""Phase 5C — Adaptive enterprise components regression."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.response_experience import plan_response_experience, render_enterprise_markdown

CASES: list[dict] = [
    {
        "question": "What is Apex National Bank's mission, vision, and core values?",
        "answer": (
            "Apex National Bank's mission is to steward clients' financial lives. "
            "Its vision is to be the most trusted and operationally resilient bank. "
            "Core values include Integrity First, Client Stewardship, and Accountability."
        ),
        "expect_layout": "definition",
        "expect_any": ["Executive Summary", "Key Takeaways"],
        "expect_rendered": ["executive_summary", "key_takeaways"],
    },
    {
        "question": "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        "answer": (
            "The metadata categories include Administrative Metadata, Business Metadata, "
            "Technical Metadata, and Compliance Metadata."
        ),
        "sources": ["002_ENTERPRISE_METADATA_STANDARD.pdf"],
        "related": [
            "003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf",
            "004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf",
        ],
        "expect_layout": "list_extraction",
        "expect_any": ["Related Documents"],
        "expect_rendered": ["related_documents"],
    },
    {
        "question": "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
        "answer": (
            "L1: Domain\nL2: Category\nL3: Sub-category\nL4: Document Type\n"
            "The hierarchy supports faceted enterprise search."
        ),
        "expect_layout": "hierarchy",
        "expect_any": ["└──"],
        "expect_rendered": ["hierarchy_tree"],
    },
    {
        "question": "What are the approval rules in the Approval Authority Matrix?",
        "answer": (
            "Approval authority is determined by document class and risk. "
            "Routine changes follow delegated authority; material changes escalate "
            "to the named committee in the matrix."
        ),
        "expect_layout": "decision_guidance",
        "expect_any": ["| Stage | Detail |"],
        "expect_rendered": ["decision_matrix"],
    },
    {
        "question": "Describe the complete governance journey.",
        "answer": (
            "The objective is controlled document handling.\n\n"
            "1. Create\n2. Review\n3. Approve\n4. Publish\n5. Retain\n6. Archive\n\n"
            "Roles include authors and approvers. The outcome is durable governance."
        ),
        "expect_layout": "workflow",
        "expect_any": ["↓", "✔ "],
        "expect_rendered": ["timeline", "checklist"],
    },
    {
        "question": "Which committee should approve this?",
        "answer": (
            "The Enterprise Risk Committee should approve material risk-policy changes. "
            "Escalate to the Board Risk Committee when thresholds in the charter are met."
        ),
        "expect_layout": "decision_guidance",
        "expect_any": ["Committee", "| Stage | Detail |"],
        "expect_rendered": ["decision_matrix"],
    },
    {
        "question": "You are the Head of Enterprise Knowledge Management. Write a 500-word overview.",
        "answer": (
            "Enterprise knowledge management connects metadata, taxonomy, naming, "
            "approval, and retention into one operating system for documents.\n\n"
            "Metadata standards define required fields at creation. "
            "Taxonomy provides the hierarchy for search. "
            "Naming and versioning keep identifiers stable. "
            "Approval matrices and committee charters establish authority. "
            "Retention policies close the lifecycle with defensible archival rules.\n\n"
            "Together these standards reduce ambiguity and improve retrieval quality."
        ),
        "related": [
            "002_ENTERPRISE_METADATA_STANDARD.pdf",
            "003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf",
            "006_APPROVAL_AUTHORITY_MATRIX.pdf",
        ],
        "sources": ["007_ENTERPRISE_COMMITTEE_CHARTER.pdf"],
        "expect_layout": "executive_report",
        "expect_any": ["Executive Summary", "Key Findings", "Related Documents"],
        "expect_rendered": ["executive_summary", "key_takeaways", "related_documents"],
    },
]


def main() -> int:
    print("=" * 60)
    print("PHASE 5C — ADAPTIVE ENTERPRISE COMPONENTS REGRESSION")
    print("=" * 60)
    failures = 0
    for case in CASES:
        question = case["question"]
        answer = case["answer"]
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
            sources=case.get("sources") or ["EXAMPLE.pdf"],
            related_documents=case.get("related"),
        )
        layout_ok = layout.layout.value == case["expect_layout"]
        text_ok = all(token in result.markdown for token in case["expect_any"])
        rendered_ok = all(
            item in result.components_rendered for item in case["expect_rendered"]
        )
        ok = layout_ok and text_ok and rendered_ok
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"\n[{status}] {question[:72]}")
        print(f"  Layout: {layout.layout.value}")
        print(f"  Requested: {result.components_requested}")
        print(f"  Rendered: {result.components_rendered}")
        print(f"  Skipped: {result.components_skipped}")
        if result.skip_reasons:
            print(f"  Skip reasons: {result.skip_reasons}")
        if not ok:
            print(
                f"  checks layout={layout_ok} text={text_ok} rendered={rendered_ok}"
            )

    print("\n" + "=" * 60)
    print(f"RESULT: {len(CASES) - failures}/{len(CASES)} passed")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
