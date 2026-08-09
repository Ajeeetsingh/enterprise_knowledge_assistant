"""Unit tests for Phase 4F answer synthesis."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.answer_synthesis import plan_answer_synthesis
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.llm.prompt_builder import PromptBuilder
from app.rag.types import RetrievalResult


def _chunk(
    chunk_id: str,
    content: str,
    *,
    section: str,
    source: str,
    page: int = 1,
) -> RetrievalResult:
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


def _bundle(question: str, results: list[RetrievalResult]):
    plan = plan_answer(question)
    graph = organize_evidence(results, answer_plan=plan)
    composition = compose_answer_evidence(graph, question=question, answer_plan=plan)
    synthesis = plan_answer_synthesis(
        question=question,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    return plan, graph, composition, synthesis


def test_mission_prefers_company_profile_primary() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    results = [
        _chunk(
            "m",
            "1.4 Mission To steward clients.",
            section="1.4 Mission",
            source="COMPANY_PROFILE.pdf",
        ),
        _chunk(
            "v",
            "1.5 Vision Most trusted bank.",
            section="1.5 Vision",
            source="COMPANY_PROFILE.pdf",
        ),
        _chunk(
            "meta",
            "Administrative Metadata fields.",
            section="Metadata",
            source="002_ENTERPRISE_METADATA_STANDARD.pdf",
        ),
    ]
    _, _, _, synthesis = _bundle(question, results)
    assert synthesis.primary_document == "COMPANY_PROFILE.pdf"
    assert synthesis.mode in {"single_document", "multi_document"}
    assert not synthesis.is_unsupported
    assert "Mission" in synthesis.concept_coverage or any(
        "Mission" in s.concept for s in synthesis.sections
    )


def test_governance_journey_concept_flow_not_document_order() -> None:
    question = "Describe the complete governance journey."
    results = [
        _chunk(
            "ret",
            "Retention follows publication.",
            section="Retention",
            source="005_RECORDS_RETENTION_POLICY.pdf",
        ),
        _chunk(
            "meta",
            "Metadata must be applied at creation.",
            section="Metadata",
            source="002_ENTERPRISE_METADATA_STANDARD.pdf",
        ),
        _chunk(
            "appr",
            "Approval is required before publication.",
            section="Approval",
            source="006_APPROVAL_AUTHORITY_MATRIX.pdf",
        ),
        _chunk(
            "name",
            "Naming and versioning at creation.",
            section="Naming",
            source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf",
        ),
    ]
    _, _, _, synthesis = _bundle(question, results)
    assert synthesis.mode == "multi_document"
    flow = synthesis.concept_flow
    assert "Metadata" in flow
    assert "Naming" in flow or "Approval" in flow
    assert "Retention" in flow
    # Canonical flow: Metadata before Retention
    assert flow.index("Metadata") < flow.index("Retention")


def test_q2_2026_profit_is_unsupported() -> None:
    question = "What was Apex National Bank's Q2 2026 profit?"
    results = [
        _chunk(
            "prof",
            "Apex National Bank mission is to steward clients. Founded decades ago.",
            section="Mission",
            source="COMPANY_PROFILE.pdf",
        ),
    ]
    _, _, _, synthesis = _bundle(question, results)
    assert synthesis.is_unsupported
    assert synthesis.mode == "unsupported"
    assert synthesis.refusal_message is not None
    assert "q2 2026" in synthesis.refusal_message.lower()
    assert "financial results" in synthesis.refusal_message.lower()


def test_prompt_has_no_retrieval_artifacts_with_synthesis() -> None:
    question = "Explain how governance standards work together."
    results = [
        _chunk(
            "meta",
            "Metadata standard defines required fields.",
            section="Metadata",
            source="002_ENTERPRISE_METADATA_STANDARD.pdf",
        ),
        _chunk(
            "tax",
            "Taxonomy hierarchy supports search.",
            section="Taxonomy",
            source="003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf",
        ),
        _chunk(
            "ret",
            "Retention policy governs archival.",
            section="Retention",
            source="005_RECORDS_RETENTION_POLICY.pdf",
        ),
    ]
    plan, graph, composition, synthesis = _bundle(question, results)
    prompt = PromptBuilder().build(
        question,
        results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
        answer_synthesis=synthesis,
    )
    lowered = prompt.user.lower()
    assert "=== primary evidence ===" not in lowered
    assert "[primary" not in lowered
    assert "chunk_ids" not in lowered
    assert "priority_score" not in lowered
    assert "rerank" not in lowered
    assert "top-k" not in lowered
    assert "similarity" not in lowered
    assert "## Metadata" in prompt.user or "Metadata" in prompt.user
    assert "PRIMARY" not in prompt.system or "Never mention internal system terms" in prompt.system


def test_metadata_question_owns_metadata_standard() -> None:
    question = "What are the different categories of metadata?"
    results = [
        _chunk(
            "meta",
            "Administrative Metadata Business Metadata Technical Metadata",
            section="Metadata Categories",
            source="002_ENTERPRISE_METADATA_STANDARD.pdf",
        ),
        _chunk(
            "tax",
            "Taxonomy levels L1 L2 L3",
            section="Hierarchy",
            source="003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf",
        ),
    ]
    _, _, _, synthesis = _bundle(question, results)
    assert synthesis.primary_document == "002_ENTERPRISE_METADATA_STANDARD.pdf"


def test_diagnostics_payload_has_required_keys() -> None:
    question = "Describe the complete governance journey."
    results = [
        _chunk(
            "a",
            "Creation and naming begin the journey.",
            section="Naming",
            source="004_DOCUMENT_NAMING_AND_VERSIONING_STANDARD.pdf",
        ),
        _chunk(
            "b",
            "Approval and committee oversight.",
            section="Approval",
            source="006_APPROVAL_AUTHORITY_MATRIX.pdf",
        ),
    ]
    _, _, _, synthesis = _bundle(question, results)
    payload = synthesis.to_dict()
    for key in (
        "primary_document",
        "supporting_documents",
        "section_ownership",
        "concept_coverage",
        "dropped_concepts",
        "document_contribution_pct",
        "unsupported_concepts",
    ):
        assert key in payload
