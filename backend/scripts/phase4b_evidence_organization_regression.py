"""Phase 4B — evidence organization regression (no retrieval / no LLM).

Builds synthetic retrieved sets for foundation/governance questions and verifies:
- all input chunk ids are preserved
- no extra chunk ids are invented
- profile-aware ordering improves coherence when signals exist
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
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
    chunk_type: str = "subsection",
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
        chunk_type=chunk_type,
    )


CASES: list[tuple[str, list[RetrievalResult], list[str]]] = [
    (
        "What is Apex National Bank's mission, vision, and core values?",
        [
            _c(
                "v",
                "1.6 Core Values Integrity First",
                source="COMPANY_PROFILE.pdf",
                page=10,
                section="1.6 Core Values",
                hierarchy=("Overview", "1.6 Core Values"),
            ),
            _c(
                "m",
                "1.4 Mission To steward clients",
                source="COMPANY_PROFILE.pdf",
                page=10,
                section="1.4 Mission",
                hierarchy=("Overview", "1.4 Mission"),
            ),
            _c(
                "vis",
                "1.5 Vision Most trusted bank",
                source="COMPANY_PROFILE.pdf",
                page=10,
                section="1.5 Vision",
                hierarchy=("Overview", "1.5 Vision"),
            ),
        ],
        ["Mission", "Vision", "Core Values"],
    ),
    (
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        [
            _c(
                "meta-toc",
                "4.1 Administrative 4.2 Business 4.3 Technical",
                source="002_ENTERPRISE_METADATA_STANDARD.pdf",
                page=12,
                section="Metadata Taxonomy",
            ),
            _c(
                "meta-body",
                "Administrative Metadata includes ownership and retention class.",
                source="002_ENTERPRISE_METADATA_STANDARD.pdf",
                page=14,
                section="Administrative Metadata",
                chunk_type="table",
            ),
        ],
        ["Administrative"],
    ),
    (
        "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
        [
            _c(
                "tax-l1",
                "L1 Domain organizes enterprise knowledge areas.",
                source="003_KNOWLEDGE_TAXONOMY.pdf",
                page=8,
                section="Hierarchy",
                hierarchy=("Taxonomy", "Hierarchy"),
            ),
            _c(
                "tax-search",
                "Hierarchy supports enterprise search by controlled facets.",
                source="003_KNOWLEDGE_TAXONOMY.pdf",
                page=18,
                section="Search Support",
            ),
        ],
        ["Hierarchy"],
    ),
    (
        "Describe the complete governance journey.",
        [
            _c(
                "g-ret",
                "Retention controls apply after publication.",
                source="005_RECORDS_RETENTION_POLICY.pdf",
                page=10,
                section="Retention",
            ),
            _c(
                "g-create",
                "Creation of controlled documents starts with drafting.",
                source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf",
                page=2,
                section="Creation",
            ),
            _c(
                "g-approve",
                "Approval precedes publication.",
                source="006_APPROVAL_AUTHORITY_MATRIX.pdf",
                page=6,
                section="Approval",
            ),
        ],
        ["Creation", "Approval", "Retention"],
    ),
    (
        "Which committee should approve this?",
        [
            _c(
                "com",
                "Enterprise Risk Committee authority for material risk decisions.",
                source="007_ENTERPRISE_COMMITTEE_CHARTER.pdf",
                page=12,
                section="Committee Mandates",
            ),
            _c(
                "esc",
                "Escalation path to the Board Risk Committee.",
                source="007_ENTERPRISE_COMMITTEE_CHARTER.pdf",
                page=20,
                section="Escalation",
            ),
        ],
        ["Committee", "Escalation"],
    ),
]


def main() -> int:
    print("=" * 60)
    print("PHASE 4B — EVIDENCE ORGANIZATION REGRESSION")
    print("=" * 60)
    failures = 0
    for question, results, expected_order_labels in CASES:
        plan = plan_answer(question)
        graph = organize_evidence(results, answer_plan=plan)
        input_ids = {r.chunk_id for r in results}
        output_ids = {cid for n in graph.nodes for cid in n.chunk_ids}
        labels = [n.label for n in graph.nodes]
        order_ok = True
        positions = []
        for token in expected_order_labels:
            idx = next((i for i, lab in enumerate(labels) if token.lower() in lab.lower()), None)
            positions.append(idx)
            if idx is None:
                order_ok = False
        if order_ok and all(p is not None for p in positions):
            order_ok = positions == sorted(positions)

        preserve_ok = input_ids == output_ids
        ok = preserve_ok and order_ok and len(graph.nodes) >= 1
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"\n[{status}] {question}")
        print(f"  Answer type: {plan.answer_type.value}")
        print(f"  Profile: {graph.structure_profile}")
        print(f"  Groups: {labels}")
        print(f"  Ordering decisions: {graph.ordering_decisions[:3]}")
        print(f"  Chunk preservation: {preserve_ok} ({sorted(output_ids)})")
        if not ok:
            print(f"  Expected label order containing: {expected_order_labels}")
            print(f"  Positions: {positions}")

    print("\n" + "=" * 60)
    print(f"RESULT: {len(CASES) - failures}/{len(CASES)} passed")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
