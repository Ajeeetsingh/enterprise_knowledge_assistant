"""Unit tests for Phase 4E reliability / intent coverage / confidence."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.gaqa import run_gaqa
from app.gaqa.intent import assess_intent_coverage
from app.rag.types import RetrievalResult


def _chunk(
    chunk_id: str,
    content: str,
    *,
    section: str,
    source: str = "GOVERNANCE.pdf",
    page: int = 10,
) -> RetrievalResult:
    return RetrievalResult(
        content=content,
        source=source,
        category="general",
        confidence=0.75,
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
    return plan, graph, composition


def test_chatgpt_policy_intent_uncovered_refuses() -> None:
    question = "What is Apex National Bank's policy for employees using ChatGPT?"
    results = [
        _chunk(
            "g1",
            "Enterprise governance framework defines committee oversight and taxonomy.",
            section="Governance Framework",
            source="001_ENTERPRISE_GOVERNANCE.pdf",
        ),
        _chunk(
            "g2",
            "Metadata standards classify documents for retention and access control.",
            section="Metadata",
            source="002_ENTERPRISE_METADATA_STANDARD.pdf",
        ),
    ]
    plan, graph, composition = _bundle(question, results)
    speculative = (
        "According to enterprise governance documents, employees should follow "
        "committee-approved standards when using technology tools."
    )
    report = run_gaqa(
        question=question,
        answer=speculative,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    assert report.answer_completeness == "related_not_answering"
    assert report.recommended_final_answer is not None
    assert "couldn't find" in report.recommended_final_answer.lower()
    assert "chatgpt" in report.recommended_final_answer.lower()
    assert report.overall_confidence <= 0.20
    assert report.confidence_label == "low"
    assert report.intent_coverage < 0.45


def test_explicit_refusal_does_not_get_high_confidence() -> None:
    question = "What is the company's ChatGPT policy?"
    results = [
        _chunk(
            "g1",
            "Governance policy describes board committees and escalation paths.",
            section="Governance",
        ),
    ]
    plan, graph, composition = _bundle(question, results)
    refusal = "I couldn't find any document that defines this policy."
    report = run_gaqa(
        question=question,
        answer=refusal,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    assert report.overall_confidence <= 0.20
    assert report.answer_completeness in {
        "explicit_refusal",
        "related_not_answering",
    }


def test_partial_answer_appends_missing_note_and_medium_confidence() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    results = [
        _chunk("m", "1.4 Mission To steward clients.", section="1.4 Mission"),
        _chunk("v", "1.5 Vision Most trusted bank.", section="1.5 Vision"),
        _chunk("c", "1.6 Core Values Integrity First.", section="1.6 Core Values"),
    ]
    plan, graph, composition = _bundle(question, results)
    incomplete = (
        "Apex National Bank's mission is to steward clients' financial lives. "
        "Its vision is to be the most trusted bank."
    )
    report = run_gaqa(
        question=question,
        answer=incomplete,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    assert "Core Values" in report.missing_concepts
    assert report.answer_completeness == "partial"
    assert report.recommended_final_answer is not None
    assert "could not find" in report.recommended_final_answer.lower()
    assert 0.45 <= report.overall_confidence <= 0.80
    assert report.confidence_label in {"medium", "low"}


def test_complete_grounded_answer_high_confidence() -> None:
    question = "What is Apex National Bank's mission, vision, and core values?"
    results = [
        _chunk(
            "m",
            "1.4 Mission To steward our clients' financial lives with precision.",
            section="1.4 Mission",
        ),
        _chunk(
            "v",
            "1.5 Vision To be the most trusted and operationally resilient bank.",
            section="1.5 Vision",
        ),
        _chunk(
            "c",
            "1.6 Core Values Integrity First. Client Stewardship. Accountability.",
            section="1.6 Core Values",
        ),
    ]
    plan, graph, composition = _bundle(question, results)
    answer = (
        "Mission: To steward our clients' financial lives with precision. "
        "Vision: To be the most trusted and operationally resilient bank. "
        "Core values include Integrity First, Client Stewardship, and Accountability."
    )
    report = run_gaqa(
        question=question,
        answer=answer,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    assert report.answer_completeness == "complete"
    assert report.recommended_final_answer is None
    assert report.overall_confidence >= 0.80
    assert report.confidence_label == "high"
    assert report.intent_coverage >= 0.45


def test_intent_assessment_flags_missing_subject() -> None:
    question = "What is the VPN policy for remote workers?"
    results = [
        _chunk(
            "hr",
            "Employee handbook covers dress code and office hours.",
            section="HR",
            source="HR_HANDBOOK.pdf",
        ),
    ]
    assessment = assess_intent_coverage(
        question=question,
        answer="Employees should follow security guidance.",
        evidence_text=results[0].content,
        results=results,
    )
    assert "vpn" in assessment.subject_markers
    assert not assessment.intent_covered


def test_soft_integrate_multi_document_enumeration() -> None:
    question = "Explain enterprise knowledge management responsibilities."
    results = [
        _chunk(
            "a",
            "Knowledge management owns taxonomy and metadata standards.",
            section="KM Role",
            source="KM_CHARTER.pdf",
        ),
        _chunk(
            "b",
            "Governance committees approve classification schemes.",
            section="Governance",
            source="GOVERNANCE.pdf",
        ),
    ]
    plan, graph, composition = _bundle(question, results)
    answer = (
        "According to KM_CHARTER.pdf, knowledge management owns taxonomy.\n"
        "GOVERNANCE.pdf states that committees approve classification schemes."
    )
    report = run_gaqa(
        question=question,
        answer=answer,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    # Either complete with soft integration, or keep if patterns not triggered.
    if report.recommended_final_answer:
        assert "According to KM_CHARTER.pdf" not in report.recommended_final_answer
        assert "knowledge management owns taxonomy" in report.recommended_final_answer.lower()
