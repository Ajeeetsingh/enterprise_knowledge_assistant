"""Phase 4D — GAQA regression (no LLM generation, synthetic answers).

Validates coverage, grounding, confidence, and that answers are never rewritten.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.gaqa import run_gaqa
from app.rag.types import RetrievalResult


def _c(chunk_id: str, content: str, *, source: str, section: str, page: int = 1) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="general",
        confidence=0.8,
        chunk_id=chunk_id,
        page_number=page,
        section_title=section,
        hierarchy_path=(section,),
        chunk_type="subsection",
    )


CASES = [
    {
        "question": "What is Apex National Bank's mission, vision, and core values?",
        "results": [
            _c("m", "1.4 Mission To steward clients.", source="COMPANY_PROFILE.pdf", section="1.4 Mission"),
            _c("v", "1.5 Vision Most trusted bank.", source="COMPANY_PROFILE.pdf", section="1.5 Vision"),
            _c("c", "1.6 Core Values Integrity First.", source="COMPANY_PROFILE.pdf", section="1.6 Core Values"),
        ],
        "good_answer": (
            "Mission: To steward clients. Vision: Most trusted bank. "
            "Core values include Integrity First."
        ),
        "bad_answer": "Mission: To steward clients. Vision: Most trusted bank.",
        "expect_missing_in_bad": ["Core Values"],
    },
    {
        "question": "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        "results": [
            _c(
                "meta",
                "Administrative Metadata Business Metadata Technical Metadata Compliance Metadata",
                source="002_ENTERPRISE_METADATA_STANDARD.pdf",
                section="Metadata Categories",
            ),
        ],
        "good_answer": (
            "The metadata categories include Administrative, Business, Technical, "
            "and Compliance metadata."
        ),
        "bad_answer": "The bank headquarters is in a coastal city with many branches.",
        "expect_missing_in_bad": ["Metadata Categories"],
    },
    {
        "question": "Describe the complete governance journey.",
        "results": [
            _c("cr", "Creation drafting begins the journey.", source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf", section="Creation"),
            _c("ap", "Approval is required before publication.", source="006_APPROVAL_AUTHORITY_MATRIX.pdf", section="Approval"),
            _c("re", "Retention follows publication.", source="005_RECORDS_RETENTION_POLICY.pdf", section="Retention"),
        ],
        "good_answer": (
            "The objective of the governance journey is controlled document handling. "
            "Steps: first creation, then approval, then retention. "
            "Roles include owning functions and approvers. Outcome is durable records."
        ),
        "bad_answer": "Retention happens first, then creation, then approval somehow.",
        "expect_missing_in_bad": [],
    },
]


def main() -> int:
    print("=" * 60)
    print("PHASE 4D — GAQA REGRESSION")
    print("=" * 60)
    failures = 0
    for case in CASES:
        question = case["question"]
        results = case["results"]
        plan = plan_answer(question)
        graph = organize_evidence(results, answer_plan=plan)
        composition = compose_answer_evidence(graph, question=question, answer_plan=plan)

        good = case["good_answer"]
        bad = case["bad_answer"]
        good_report = run_gaqa(
            question=question,
            answer=good,
            results=results,
            answer_plan=plan,
            evidence_graph=graph,
            answer_composition=composition,
        )
        bad_report = run_gaqa(
            question=question,
            answer=bad,
            results=results,
            answer_plan=plan,
            evidence_graph=graph,
            answer_composition=composition,
        )

        rewrite_ok = good == case["good_answer"] and bad == case["bad_answer"]
        confidence_ok = good_report.overall_confidence >= bad_report.overall_confidence
        missing_ok = all(
            concept in bad_report.missing_concepts
            for concept in case["expect_missing_in_bad"]
        )
        mapping_ok = bool(good_report.evidence_mappings)

        ok = rewrite_ok and confidence_ok and missing_ok and mapping_ok
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1

        print(f"\n[{status}] {question}")
        print(
            f"  Good confidence: {good_report.confidence_label} "
            f"({good_report.overall_confidence:.3f})"
        )
        print(
            f"  Bad confidence: {bad_report.confidence_label} "
            f"({bad_report.overall_confidence:.3f})"
        )
        print(f"  Good missing: {good_report.missing_concepts}")
        print(f"  Bad missing: {bad_report.missing_concepts}")
        print(f"  Ordering ok (good/bad): {good_report.ordering_ok}/{bad_report.ordering_ok}")
        print(f"  Answer rewritten?: {not rewrite_ok}")
        if not ok:
            print(
                f"  checks rewrite={rewrite_ok} confidence={confidence_ok} "
                f"missing={missing_ok} mapping={mapping_ok}"
            )

    print("\n" + "=" * 60)
    print(f"RESULT: {len(CASES) - failures}/{len(CASES)} passed")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
