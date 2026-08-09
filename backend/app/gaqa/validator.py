"""GAQA entrypoint — validate a generated answer (Phases 4D/4E).

Checks never invent evidence. Reliability may *recommend* a final answer
override (refusal / partial note); the engine applies it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.gaqa.checks import (
    check_blueprint_compliance,
    check_evidence_mapping,
    check_ordering,
    check_question_coverage,
    check_redundancy,
    check_unsupported_claims,
)
from app.gaqa.concepts import extract_question_concepts
from app.gaqa.confidence import score_confidence
from app.gaqa.intent import assess_intent_coverage
from app.gaqa.reliability import decide_reliability
from app.gaqa.types import GaqaReport
from app.rag.types import RetrievalResult

if TYPE_CHECKING:
    from app.answer_planning.types import AnswerPlan
    from app.evidence_composition.types import AnswerComposition
    from app.evidence_organization.types import EvidenceGraph


def _evidence_corpus(
    results: list[RetrievalResult],
    composition: AnswerComposition | None,
    graph: EvidenceGraph | None,
) -> str:
    parts: list[str] = []
    if composition is not None:
        for item in composition.all_items:
            parts.extend(item.node.evidence_texts)
    elif graph is not None:
        for node in graph.nodes:
            parts.extend(node.evidence_texts)
    else:
        parts.extend(item.content or "" for item in results)
    return "\n".join(parts)


def run_gaqa(
    *,
    question: str,
    answer: str,
    results: list[RetrievalResult],
    answer_plan: AnswerPlan | None = None,
    evidence_graph: EvidenceGraph | None = None,
    answer_composition: AnswerComposition | None = None,
) -> GaqaReport:
    """Run deterministic grounded-answer quality checks + reliability judgment.

    Does not mutate the ``answer`` string in-place. Populates
    ``recommended_final_answer`` when a reliability override is warranted.
    """
    report = GaqaReport()
    evidence_text = _evidence_corpus(results, answer_composition, evidence_graph)

    coverage, missing = check_question_coverage(question, answer, evidence_text)
    report.question_coverage = coverage
    report.missing_concepts = missing

    sections, compliance = check_blueprint_compliance(answer, answer_plan)
    report.blueprint_sections = sections
    report.blueprint_compliance = compliance

    report.evidence_mappings = check_evidence_mapping(
        answer, answer_composition, evidence_graph
    )

    claims, unsupported = check_unsupported_claims(answer, evidence_text)
    report.claim_support = claims
    report.unsupported_claim_count = unsupported

    concepts = extract_question_concepts(question)
    report.redundant_concepts = check_redundancy(answer, concepts)

    ordering_ok, ordering_notes = check_ordering(answer, answer_plan)
    report.ordering_ok = ordering_ok
    report.ordering_notes = ordering_notes

    intent = assess_intent_coverage(
        question=question,
        answer=answer,
        evidence_text=evidence_text,
        results=results,
    )
    report.intent_coverage = intent.intent_coverage
    report.evidence_specificity = intent.evidence_specificity
    report.question_match = intent.question_match

    decision = decide_reliability(
        question=question,
        answer=answer,
        report=report,
        intent=intent,
        has_results=bool(results),
    )
    report.answer_completeness = decision.completeness.value
    report.refusal_reason = decision.refusal_reason
    report.reliability_notes = list(decision.notes)
    report.recommended_final_answer = decision.final_answer

    if missing:
        report.decisions.append(f"missing_concepts={missing}")
    if unsupported:
        report.decisions.append(f"unsupported_claims={unsupported}")
    if report.redundant_concepts:
        report.decisions.append(f"redundancy={report.redundant_concepts}")
    if not ordering_ok:
        report.decisions.append("ordering_issue")
    report.decisions.append(f"intent_coverage={intent.intent_coverage:.3f}")
    report.decisions.append(f"evidence_specificity={intent.evidence_specificity:.3f}")
    report.decisions.append(f"answer_completeness={decision.completeness.value}")
    if decision.refusal_reason:
        report.decisions.append(f"refusal_reason={decision.refusal_reason}")
    for reason in intent.reasons:
        report.decisions.append(reason)

    return score_confidence(report)
