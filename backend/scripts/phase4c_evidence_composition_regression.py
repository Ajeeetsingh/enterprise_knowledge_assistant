"""Phase 4C — evidence prioritization regression (no retrieval / no LLM).

Verifies primary/supporting/optional composition for foundation questions while
preserving organized chunk ids.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.rag.types import RetrievalResult


def _c(
    chunk_id: str,
    content: str,
    *,
    source: str,
    page: int,
    section: str,
    hierarchy: tuple[str, ...] | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="general",
        confidence=0.75,
        chunk_id=chunk_id,
        page_number=page,
        section_title=section,
        hierarchy_path=hierarchy or (section,),
        chunk_type="subsection",
    )


CASES: list[tuple[str, list[RetrievalResult], list[str], list[str]]] = [
    (
        "What is Apex National Bank's mission, vision, and core values?",
        [
            _c("h", "1.3 History founded long ago", source="COMPANY_PROFILE.pdf", page=8, section="1.3 History", hierarchy=("Overview", "1.3 History")),
            _c("m", "1.4 Mission To steward clients", source="COMPANY_PROFILE.pdf", page=10, section="1.4 Mission", hierarchy=("Overview", "1.4 Mission")),
            _c("v", "1.5 Vision Most trusted bank", source="COMPANY_PROFILE.pdf", page=10, section="1.5 Vision", hierarchy=("Overview", "1.5 Vision")),
            _c("c", "1.6 Core Values Integrity First", source="COMPANY_PROFILE.pdf", page=10, section="1.6 Core Values", hierarchy=("Overview", "1.6 Core Values")),
            _c("hq", "Headquarters location details", source="COMPANY_PROFILE.pdf", page=12, section="Headquarters"),
        ],
        ["Mission", "Vision", "Core Values"],
        ["History", "Headquarters"],
    ),
    (
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        [
            _c("meta", "Administrative Metadata Business Metadata Technical Metadata", source="002_ENTERPRISE_METADATA_STANDARD.pdf", page=14, section="Metadata Categories"),
            _c("app", "Appendix reference tables", source="002_ENTERPRISE_METADATA_STANDARD.pdf", page=40, section="Appendix"),
        ],
        ["Metadata", "Categories", "Administrative"],
        ["Appendix"],
    ),
    (
        "Describe the complete governance journey.",
        [
            _c("create", "Creation drafting controlled documents", source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf", page=2, section="Creation"),
            _c("approve", "Approval before publication", source="006_APPROVAL_AUTHORITY_MATRIX.pdf", page=6, section="Approval"),
            _c("retain", "Retention after publication", source="005_RECORDS_RETENTION_POLICY.pdf", page=10, section="Retention"),
            _c("hist", "Appendix History of early controls", source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf", page=28, section="Appendix History"),
        ],
        ["Creation", "Approval", "Retention"],
        ["History", "Appendix"],
    ),
    (
        "Which committee should approve this?",
        [
            _c("com", "Enterprise Risk Committee approval authority", source="007_ENTERPRISE_COMMITTEE_CHARTER.pdf", page=12, section="Committee Mandates"),
            _c("esc", "Escalation path to Board Risk Committee", source="007_ENTERPRISE_COMMITTEE_CHARTER.pdf", page=20, section="Escalation"),
            _c("hist", "History of committee formation", source="007_ENTERPRISE_COMMITTEE_CHARTER.pdf", page=3, section="History"),
        ],
        ["Committee", "Escalation", "Approval", "Authority"],
        ["History"],
    ),
]


def _contains_any(labels: list[str], tokens: list[str]) -> bool:
    joined = " ".join(labels).lower()
    return any(token.lower() in joined for token in tokens)


def main() -> int:
    print("=" * 60)
    print("PHASE 4C — EVIDENCE COMPOSITION REGRESSION")
    print("=" * 60)
    failures = 0
    for question, results, primary_tokens, optional_tokens in CASES:
        plan = plan_answer(question)
        graph = organize_evidence(results, answer_plan=plan)
        composition = compose_answer_evidence(graph, question=question, answer_plan=plan)

        input_ids = {r.chunk_id for r in results}
        graph_ids = {cid for n in graph.nodes for cid in n.chunk_ids}
        comp_ids = {cid for item in composition.all_items for cid in item.node.chunk_ids}
        preserve_ok = input_ids == graph_ids == comp_ids

        primary_labels = [item.node.label for item in composition.primary]
        optional_labels = [item.node.label for item in composition.optional]
        primary_ok = _contains_any(primary_labels, primary_tokens)
        optional_ok = _contains_any(optional_labels, optional_tokens) or not optional_tokens

        ok = preserve_ok and primary_ok and bool(composition.primary)
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1

        print(f"\n[{status}] {question}")
        print(f"  Answer type: {plan.answer_type.value}")
        print(f"  Primary: {primary_labels}")
        print(f"  Supporting: {[i.node.label for i in composition.supporting]}")
        print(f"  Optional: {optional_labels}")
        print(f"  Chunk preservation: {preserve_ok}")
        if not optional_ok:
            print(f"  NOTE: expected optional-ish tokens among {optional_tokens}")
        if not ok:
            print(f"  Expected primary tokens among: {primary_tokens}")

    print("\n" + "=" * 60)
    print(f"RESULT: {len(CASES) - failures}/{len(CASES)} passed")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
