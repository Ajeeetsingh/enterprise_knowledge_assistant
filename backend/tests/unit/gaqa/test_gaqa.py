"""Unit tests for Phase 4D GAQA."""

from __future__ import annotations

from app.answer_planning import plan_answer
from app.evidence_composition import compose_answer_evidence
from app.evidence_organization import organize_evidence
from app.gaqa import run_gaqa
from app.gaqa.concepts import extract_question_concepts
from app.rag.types import RetrievalResult


def _chunk(
    chunk_id: str,
    content: str,
    *,
    section: str,
    source: str = "COMPANY_PROFILE.pdf",
    page: int = 10,
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
    return plan, graph, composition


def test_extracts_mission_vision_core_values_concepts() -> None:
    concepts = extract_question_concepts(
        "What is Apex National Bank's mission, vision, and core values?"
    )
    assert "Mission" in concepts
    assert "Vision" in concepts
    assert "Core Values" in concepts


def test_detects_missing_concept_without_rewriting_answer() -> None:
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
    assert incomplete == incomplete  # answer not rewritten by GAQA
    # Confidence should be reduced vs a complete answer.
    complete = (
        incomplete
        + " Core values include Integrity First, Client Stewardship, and Accountability."
    )
    complete_report = run_gaqa(
        question=question,
        answer=complete,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    assert complete_report.overall_confidence > report.overall_confidence
    assert not complete_report.missing_concepts


def test_evidence_mapping_and_supported_claims() -> None:
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
    assert report.confidence_label in {"high", "medium"}
    assert report.component_scores["grounding"] >= 0.5
    assert all(item.chunk_ids for item in report.evidence_mappings)
    assert report.unsupported_claim_count == 0 or report.component_scores["unsupported_rate"] < 0.5


def test_unsupported_claim_detection() -> None:
    question = "What is Apex National Bank's mission?"
    results = [
        _chunk("m", "1.4 Mission To steward clients.", section="1.4 Mission"),
    ]
    plan, graph, composition = _bundle(question, results)
    answer = (
        "The mission is to steward clients. "
        "Additionally, the bank secretly operates a Martian colony and invents quantum currency daily."
    )
    report = run_gaqa(
        question=question,
        answer=answer,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    assert report.unsupported_claim_count >= 1
    assert any(item.support == "unsupported" for item in report.claim_support)


def test_gaqa_does_not_mutate_answer_text() -> None:
    question = "What are the different categories of metadata?"
    results = [
        _chunk(
            "meta",
            "Administrative Metadata Business Metadata Technical Metadata",
            section="Metadata Categories",
            source="002_ENTERPRISE_METADATA_STANDARD.pdf",
        ),
    ]
    plan, graph, composition = _bundle(question, results)
    answer = "The metadata categories include Administrative, Business, and Technical metadata."
    before = answer
    report = run_gaqa(
        question=question,
        answer=answer,
        results=results,
        answer_plan=plan,
        evidence_graph=graph,
        answer_composition=composition,
    )
    assert answer == before
    assert report.overall_confidence >= 0.0
