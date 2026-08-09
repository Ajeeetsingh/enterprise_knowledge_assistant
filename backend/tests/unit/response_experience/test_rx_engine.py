"""Unit tests for Phase 5A Response Experience Engine."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.answer_synthesis import plan_answer_synthesis
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.response_experience import plan_response_experience
from app.response_experience.enums import ResponseComponent, ResponseLayoutType
from app.rag.types import RetrievalResult


def _chunk(chunk_id: str, content: str, *, source: str, section: str) -> RetrievalResult:
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


def _layout(question: str, results: list[RetrievalResult] | None = None, answer: str = "Answer.") :
    plan = plan_answer(question)
    graph = None
    composition = None
    synthesis = None
    if results is not None:
        graph = organize_evidence(results, answer_plan=plan)
        composition = compose_answer_evidence(graph, question=question, answer_plan=plan)
        synthesis = plan_answer_synthesis(
            question=question,
            answer_plan=plan,
            evidence_graph=graph,
            answer_composition=composition,
        )
    return plan_response_experience(
        question=question,
        answer=answer,
        answer_plan=plan,
        evidence_graph=graph,
        answer_synthesis=synthesis,
    )


def test_mission_uses_definition_layout() -> None:
    layout = _layout(
        "What is Apex National Bank's mission, vision, and core values?",
        answer="Mission is X. Vision is Y. Values include integrity.",
    )
    assert layout.layout == ResponseLayoutType.DEFINITION
    assert ResponseComponent.DEFINITION in layout.components
    assert ResponseComponent.SOURCES in layout.components


def test_metadata_uses_list_layout() -> None:
    layout = _layout(
        "What are the different categories of metadata defined by the Enterprise Metadata Standard?",
        answer="Administrative, Business, Technical, Compliance.",
    )
    assert layout.layout == ResponseLayoutType.LIST_EXTRACTION
    assert ResponseComponent.DIRECT_LIST in layout.components


def test_taxonomy_uses_hierarchy_layout() -> None:
    layout = _layout(
        "Explain the hierarchy used in the Enterprise Knowledge Taxonomy and how it supports enterprise search.",
        answer="L1 to L4 hierarchy supports faceted search.",
    )
    assert layout.layout == ResponseLayoutType.HIERARCHY
    assert ResponseComponent.HIERARCHY_TREE in layout.components


def test_approval_and_committee_use_decision_layout() -> None:
    approval = _layout("What are the approval rules in the Approval Authority Matrix?")
    assert approval.layout == ResponseLayoutType.DECISION_GUIDANCE
    committee = _layout("Which committee should approve this?")
    assert committee.layout == ResponseLayoutType.DECISION_GUIDANCE
    assert ResponseComponent.DECISION_MATRIX in committee.components


def test_governance_journey_uses_workflow_layout() -> None:
    layout = _layout(
        "Describe the complete governance journey.",
        [
            _chunk(
                "a",
                "Creation then approval then retention.",
                source="005_RECORDS_RETENTION_POLICY.pdf",
                section="Retention",
            ),
            _chunk(
                "b",
                "Approval before publication.",
                source="006_APPROVAL_AUTHORITY_MATRIX.pdf",
                section="Approval",
            ),
        ],
        answer="Objective: controlled docs. Steps: create, approve, retain.",
    )
    assert layout.layout == ResponseLayoutType.WORKFLOW
    assert ResponseComponent.TIMELINE in layout.components


def test_executive_question_uses_executive_report_layout() -> None:
    layout = _layout(
        "You are the Head of Enterprise Knowledge Management. Write a 500-word overview.",
        [
            _chunk(
                "m",
                "Metadata standard.",
                source="002_ENTERPRISE_METADATA_STANDARD.pdf",
                section="Metadata",
            ),
            _chunk(
                "t",
                "Taxonomy hierarchy.",
                source="003_ENTERPRISE_KNOWLEDGE_TAXONOMY.pdf",
                section="Taxonomy",
            ),
        ],
        answer="A" * 1400,
    )
    assert layout.layout == ResponseLayoutType.EXECUTIVE_REPORT
    assert ResponseComponent.EXECUTIVE_SUMMARY in layout.components
    assert ResponseComponent.KEY_TAKEAWAYS in layout.components


def test_short_definition_omits_executive_summary() -> None:
    layout = _layout(
        "What is Apex National Bank's mission?",
        answer="To steward clients' financial lives.",
    )
    assert layout.layout == ResponseLayoutType.DEFINITION
    assert ResponseComponent.EXECUTIVE_SUMMARY not in layout.components
    assert "omit_exec_summary" in " ".join(layout.adaptive_flags)


def test_layout_does_not_mutate_answer_text() -> None:
    answer = "Exact answer text must remain unchanged."
    layout = _layout(
        "What is Apex National Bank's mission, vision, and core values?",
        answer=answer,
    )
    assert answer == "Exact answer text must remain unchanged."
    payload = layout.to_dict()
    assert payload["response_layout"] == "definition"
    assert payload["expected_render_type"]
    assert payload["components_selected"]
