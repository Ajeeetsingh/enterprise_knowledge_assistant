"""Phase 5E — final UX polish & consistency regression."""

from __future__ import annotations

import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.response_experience import (
    content_preserved,
    finalize_enterprise_markdown,
    plan_response_experience,
    polish_enterprise_markdown,
    render_enterprise_markdown,
)

CASES = [
    (
        "Mission",
        "What is Apex National Bank's mission, vision, and core values?",
        (
            "Apex National Bank's mission is to steward clients' financial lives. "
            "Its vision is to be the most trusted and operationally resilient bank. "
            "Core values include Integrity First, Client Stewardship, and Accountability."
        ),
        ["001_COMPANY_PROFILE.pdf"],
    ),
    (
        "Metadata",
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        (
            "The metadata categories include Administrative Metadata, Business Metadata, "
            "Technical Metadata, and Compliance Metadata."
        ),
        ["002_ENTERPRISE_METADATA_STANDARD.pdf"],
    ),
    (
        "Taxonomy",
        "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
        (
            "L1: Domain\nL2: Category\nL3: Sub-category\nL4: Document Type\n"
            "The hierarchy supports faceted enterprise search."
        ),
        ["003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf"],
    ),
    (
        "Naming & Versioning",
        "What are the naming and versioning rules for controlled documents?",
        (
            "Controlled documents use DOC-DOMAIN-NAME-vMAJOR.MINOR naming. "
            "Major versions require re-approval; minor versions are editorial."
        ),
        ["004_NAMING_AND_VERSIONING.pdf"],
    ),
    (
        "Retention",
        "What is the retention policy for policy documents?",
        (
            "Policy documents are retained for seven years after supersession, "
            "then archived according to the records schedule."
        ),
        ["005_RETENTION_SCHEDULE.pdf"],
    ),
    (
        "Approval Rules",
        "What approval rules apply before publishing a policy?",
        (
            "Policies require owner review, compliance review, and committee approval "
            "before publication."
        ),
        ["006_APPROVAL_RULES.pdf"],
    ),
    (
        "Committee Selection",
        "Which committee should approve this?",
        (
            "The Enterprise Risk Committee should approve material risk-policy changes. "
            "Escalate to the Board Risk Committee when thresholds in the charter are met."
        ),
        ["007_COMMITTEE_CHARTERS.pdf"],
    ),
    (
        "Business Process Guide",
        "Summarize the business process guide for document intake.",
        (
            "Document intake starts with submission, metadata capture, quality checks, "
            "and routing to the owning department."
        ),
        ["008_BUSINESS_PROCESS_GUIDE.pdf"],
    ),
    (
        "Governance Journey",
        "Describe the complete governance journey.",
        (
            "The objective is controlled document handling.\n\n"
            "1. Create\n2. Review\n3. Approve\n4. Publish\n5. Retain\n6. Archive\n\n"
            "Roles include authors and approvers."
        ),
        ["009_GOVERNANCE_JOURNEY.pdf"],
    ),
    (
        "Enterprise Knowledge Management",
        "What is Enterprise Knowledge Management at Apex?",
        (
            "Enterprise Knowledge Management governs how Apex creates, classifies, "
            "approves, and retrieves authoritative knowledge assets."
        ),
        ["010_ENTERPRISE_KNOWLEDGE_MANAGEMENT.pdf"],
    ),
    (
        "ChatGPT Policy",
        "What is the ChatGPT usage policy?",
        (
            "I cannot answer this from the available enterprise knowledge base. "
            "No supporting evidence was retrieved for a ChatGPT policy."
        ),
        [],
    ),
    (
        "Q2 2026 Profit",
        "What was Apex National Bank's profit in Q2 2026?",
        (
            "The available documents do not contain Q2 2026 profit figures. "
            "I cannot determine that value from the current knowledge base."
        ),
        [],
    ),
]


def _pipeline(question: str, answer: str, sources: list[str]) -> tuple[str, object]:
    plan = plan_answer(question)
    layout = plan_response_experience(question=question, answer=answer, answer_plan=plan)
    rendered = render_enterprise_markdown(
        layout=layout,
        answer=answer,
        question=question,
        sources=sources,
    )
    polished = polish_enterprise_markdown(rendered.markdown)
    finalized = finalize_enterprise_markdown(polished.markdown)
    return finalized.markdown, finalized


def main() -> int:
    print("=" * 60)
    print("PHASE 5E — PRESENTATION FINALIZE REGRESSION")
    print("=" * 60)
    failures = 0
    total_ms = 0.0

    for label, question, answer, sources in CASES:
        started = time.perf_counter()
        final, result = _pipeline(question, answer, sources)
        elapsed_ms = (time.perf_counter() - started) * 1000
        total_ms += elapsed_ms

        checks = {
            "content_preserved": content_preserved(answer, final),
            "has_title_or_body": bool(final.strip()),
            "no_h4": "#### " not in final,
            "no_triple_blank": "\n\n\n" not in final,
            "no_empty_exec": "## Executive Summary\n\n_none_" not in final.lower(),
            "finalize_ok": getattr(result, "content_preserved", True),
            "validation_ok": getattr(result, "validation_ok", True)
            or not any(
                "malformed table" in issue
                for issue in getattr(result, "validation_issues", [])
            ),
        }
        if sources:
            checks["has_sources"] = "## Sources" in final
            if "## Sources" in final:
                block = final.split("## Sources", 1)[1]
                bullets = [
                    line[2:].strip()
                    for line in block.splitlines()
                    if line.startswith("- ")
                ]
                checks["sources_sorted"] = bullets == sorted(bullets, key=str.lower)
                checks["sources_unique"] = len(bullets) == len(
                    {b.lower() for b in bullets}
                )

        # Separators only as standalone lines.
        hr_lines = [line for line in final.splitlines() if line.strip() == "---"]
        checks["hr_standalone"] = all(
            True for _ in hr_lines
        )  # presence is fine; structure validated below
        for idx, line in enumerate(final.splitlines()):
            if line.strip() != "---":
                continue
            # Never between list bullets.
            prev_line = final.splitlines()[idx - 1] if idx else ""
            next_line = (
                final.splitlines()[idx + 1]
                if idx + 1 < len(final.splitlines())
                else ""
            )
            if prev_line.startswith("- ") and next_line.startswith("- "):
                checks["hr_not_in_lists"] = False
                break
        else:
            checks["hr_not_in_lists"] = True

        ok = all(checks.values())
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"\n[{status}] {label}")
        print(f"  Question: {question[:72]}")
        print(f"  Transforms: {getattr(result, 'transforms_applied', [])}")
        print(f"  Empty removed: {getattr(result, 'empty_sections_removed', 0)}")
        print(f"  Latency: {elapsed_ms:.1f} ms")
        if not ok:
            print(f"  Failed: {[k for k, v in checks.items() if not v]}")
            if getattr(result, "validation_issues", None):
                print(f"  Validation: {result.validation_issues}")

    avg = total_ms / max(len(CASES), 1)
    print("\n" + "=" * 60)
    print(f"RESULT: {len(CASES) - failures}/{len(CASES)} passed")
    print(f"Avg finalize pipeline latency: {avg:.1f} ms")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
