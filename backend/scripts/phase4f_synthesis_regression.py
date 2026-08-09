"""Phase 4F — multi-document synthesis regression (no LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.answer_planning import plan_answer
from app.answer_synthesis import plan_answer_synthesis
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.llm.prompt_builder import PromptBuilder
from app.rag.types import RetrievalResult


def _c(chunk_id: str, content: str, *, source: str, section: str) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="general",
        confidence=0.8,
        chunk_id=chunk_id,
        page_number=1,
        section_title=section,
        hierarchy_path=(section,),
        chunk_type="subsection",
    )


def _run(question: str, results: list[RetrievalResult]):
    plan = plan_answer(question)
    graph = organize_evidence(results, answer_plan=plan)
    composition = compose_answer_evidence(graph, question=question, answer_plan=plan)
    synthesis = plan_answer_synthesis(
        question=question,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    prompt = PromptBuilder().build(
        question,
        results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
        answer_synthesis=synthesis,
    )
    return synthesis, prompt


def main() -> int:
    failures: list[str] = []

    # Mission ownership
    s1, p1 = _run(
        "What is Apex National Bank's mission, vision, and core values?",
        [
            _c("m", "Mission To steward clients.", source="COMPANY_PROFILE.pdf", section="Mission"),
            _c("v", "Vision Most trusted bank.", source="COMPANY_PROFILE.pdf", section="Vision"),
            _c("c", "Core Values Integrity First.", source="COMPANY_PROFILE.pdf", section="Core Values"),
        ],
    )
    if s1.primary_document != "COMPANY_PROFILE.pdf":
        failures.append(f"mission primary={s1.primary_document}")
    if "PRIMARY EVIDENCE" in p1.user:
        failures.append("mission prompt leaked PRIMARY EVIDENCE")

    # Governance multi-doc flow
    s2, p2 = _run(
        "Describe the complete governance journey.",
        [
            _c("r", "Retention after publication.", source="005_RECORDS_RETENTION_POLICY.pdf", section="Retention"),
            _c("m", "Metadata at creation.", source="002_ENTERPRISE_METADATA_STANDARD.pdf", section="Metadata"),
            _c("a", "Approval before publication.", source="006_APPROVAL_AUTHORITY_MATRIX.pdf", section="Approval"),
            _c("n", "Naming at creation.", source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf", section="Naming"),
        ],
    )
    if s2.mode != "multi_document":
        failures.append(f"governance mode={s2.mode}")
    if "Metadata" in s2.concept_flow and "Retention" in s2.concept_flow:
        if s2.concept_flow.index("Metadata") > s2.concept_flow.index("Retention"):
            failures.append(f"governance flow order={s2.concept_flow}")
    else:
        failures.append(f"governance missing concepts={s2.concept_flow}")
    artifact_markers = (
        "=== PRIMARY EVIDENCE ===",
        "[PRIMARY ",
        "chunk_ids:",
        "priority_score:",
        "rerank",
        "top-k",
    )
    if any(marker in p2.user for marker in artifact_markers):
        failures.append("governance prompt has document/PRIMARY artifacts")

    # Q2 profit unsupported
    s3, p3 = _run(
        "What was Apex National Bank's Q2 2026 profit?",
        [
            _c(
                "p",
                "Company profile mission and vision statements.",
                source="COMPANY_PROFILE.pdf",
                section="Mission",
            ),
        ],
    )
    if not s3.is_unsupported:
        failures.append("q2 profit not unsupported")
    if not s3.refusal_message or "financial results" not in s3.refusal_message.lower():
        failures.append("q2 profit refusal message weak")

    # Executive synthesis mode
    s4, _p4 = _run(
        "You are the Head of Enterprise Knowledge Management. Write a 500-word overview.",
        [
            _c("m", "Metadata standard fields.", source="002_ENTERPRISE_METADATA_STANDARD.pdf", section="Metadata"),
            _c("t", "Taxonomy hierarchy.", source="003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf", section="Taxonomy"),
            _c("c", "Committee charter oversight.", source="007_ENTERPRISE_COMMITTEE_CHARTER.pdf", section="Committee"),
            _c("r", "Retention controls.", source="005_RECORDS_RETENTION_POLICY.pdf", section="Retention"),
        ],
    )
    if s4.mode != "executive":
        failures.append(f"executive mode={s4.mode}")
    if len(s4.sections) < 3:
        failures.append(f"executive sections too few={len(s4.sections)}")

    # Metadata ownership
    s5, _p5 = _run(
        "What are the metadata categories in the Enterprise Metadata Standard?",
        [
            _c(
                "meta",
                "Administrative Business Technical Compliance metadata.",
                source="002_ENTERPRISE_METADATA_STANDARD.pdf",
                section="Categories",
            ),
            _c(
                "tax",
                "Taxonomy levels.",
                source="003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf",
                section="Hierarchy",
            ),
        ],
    )
    if s5.primary_document != "002_ENTERPRISE_METADATA_STANDARD.pdf":
        failures.append(f"metadata primary={s5.primary_document}")

    if failures:
        print("FAIL Phase 4F synthesis regression:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("PASS Phase 4F synthesis regression")
    print(f"  mission primary={s1.primary_document} mode={s1.mode}")
    print(f"  governance flow={s2.concept_flow}")
    print(f"  q2 unsupported={s3.is_unsupported}")
    print(f"  executive sections={len(s4.sections)} mode={s4.mode}")
    print(f"  metadata primary={s5.primary_document}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
