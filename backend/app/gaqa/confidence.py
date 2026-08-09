"""Deterministic confidence from GAQA component scores (Phases 4D/4E).

Confidence reflects answer quality, not retrieval quality.
"""

from __future__ import annotations

from app.gaqa.reliability import AnswerCompleteness
from app.gaqa.types import GaqaReport


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_confidence(report: GaqaReport) -> GaqaReport:
    """Populate overall/component confidence fields on an in-progress report."""
    coverage_items = report.question_coverage
    if coverage_items:
        question_coverage = sum(
            1 for item in coverage_items if item.present_in_answer
        ) / len(coverage_items)
        concept_coverage = sum(
            1
            for item in coverage_items
            if item.present_in_answer and item.present_in_evidence
        ) / len(coverage_items)
    else:
        # No extractable concepts — treat as neutral rather than perfect.
        question_coverage = 0.75
        concept_coverage = 0.75

    mappings = report.evidence_mappings
    if mappings:
        supported = sum(1 for item in mappings if item.support == "supported")
        partial = sum(1 for item in mappings if item.support == "partially_supported")
        grounding = (supported + 0.5 * partial) / len(mappings)
        primary_util = sum(1 for item in mappings if item.mentioned_in_answer) / len(
            mappings
        )
    else:
        grounding = 0.5
        primary_util = 0.5

    claims = report.claim_support
    if claims:
        unsupported_rate = report.unsupported_claim_count / max(1, len(claims))
    else:
        unsupported_rate = 0.0

    blueprint = report.blueprint_compliance
    redundancy_penalty = min(0.25, 0.05 * len(report.redundant_concepts))
    ordering_score = 1.0 if report.ordering_ok else 0.40
    ordering_penalty = 0.0 if report.ordering_ok else 0.14
    evidence_density = primary_util

    intent_cov = _clamp01(report.intent_coverage)
    specificity = _clamp01(report.evidence_specificity)
    q_match = _clamp01(report.question_match)

    try:
        completeness = AnswerCompleteness(report.answer_completeness)
    except ValueError:
        completeness = AnswerCompleteness.COMPLETE

    base = (
        0.18 * question_coverage
        + 0.12 * concept_coverage
        + 0.18 * grounding
        + 0.10 * blueprint
        + 0.08 * evidence_density
        + 0.08 * (1.0 - unsupported_rate)
        + 0.06 * ordering_score
        + 0.12 * intent_cov
        + 0.05 * specificity
        + 0.03 * q_match
        - redundancy_penalty
        - ordering_penalty
    )
    base = _clamp01(base)

    incomplete_penalty = 0.0
    refusal_factor = 1.0

    if completeness == AnswerCompleteness.NO_EVIDENCE:
        overall = 0.03
        incomplete_penalty = 0.50
        refusal_factor = 0.0
    elif completeness in {
        AnswerCompleteness.RELATED_NOT_ANSWERING,
        AnswerCompleteness.EXPLICIT_REFUSAL,
    }:
        # Honest refusal / related-but-not-answering → intentionally low.
        overall = 0.12 if intent_cov < 0.35 else 0.15
        if completeness == AnswerCompleteness.EXPLICIT_REFUSAL and intent_cov >= 0.45:
            overall = min(0.20, overall + 0.05)
        incomplete_penalty = 0.40
        refusal_factor = 0.15
    elif completeness == AnswerCompleteness.PARTIAL:
        # Target band ~0.65–0.78 for typical partials.
        overall = _clamp01(0.58 + 0.22 * base - 0.10 * (1.0 - intent_cov))
        incomplete_penalty = 0.18
        overall = _clamp01(overall - 0.04)
        if overall > 0.78:
            overall = 0.70 + 0.08 * min(1.0, grounding)
        if overall < 0.45:
            overall = 0.45 + 0.10 * grounding
    else:
        overall = base
        # Strong complete answers land near 0.90–0.98.
        if (
            question_coverage >= 0.85
            and grounding >= 0.80
            and intent_cov >= 0.70
            and unsupported_rate <= 0.05
            and specificity >= 0.40
            and report.ordering_ok
        ):
            overall = max(overall, 0.92)
            overall = min(0.98, overall + 0.03)
        elif intent_cov < 0.55 or specificity < 0.30:
            overall = min(overall, 0.55)
        if not report.ordering_ok:
            overall = min(overall, 0.78)

    overall = _clamp01(overall)

    if overall >= 0.80:
        label = "high"
    elif overall >= 0.55:
        label = "medium"
    else:
        label = "low"

    # Composite reliability for diagnostics.
    if completeness == AnswerCompleteness.NO_EVIDENCE:
        reliability = 0.05
    elif completeness in {
        AnswerCompleteness.RELATED_NOT_ANSWERING,
        AnswerCompleteness.EXPLICIT_REFUSAL,
    }:
        reliability = _clamp01(0.10 + 0.20 * intent_cov)
    elif completeness == AnswerCompleteness.PARTIAL:
        reliability = _clamp01(
            0.55 * overall + 0.25 * intent_cov + 0.20 * specificity
        )
    else:
        reliability = _clamp01(
            0.50 * overall + 0.30 * intent_cov + 0.20 * q_match
        )

    report.component_scores = {
        "question_coverage": question_coverage,
        "concept_coverage": concept_coverage,
        "grounding": grounding,
        "blueprint_compliance": blueprint,
        "evidence_density": evidence_density,
        "primary_evidence_utilization": primary_util,
        "unsupported_rate": unsupported_rate,
        "ordering": ordering_score,
        "ordering_penalty": ordering_penalty,
        "redundancy_penalty": redundancy_penalty,
        "intent_coverage": intent_cov,
        "evidence_specificity": specificity,
        "question_match": q_match,
        "incomplete_penalty": incomplete_penalty,
        "refusal_factor": refusal_factor,
    }
    report.overall_score = overall
    report.overall_confidence = overall
    report.confidence_label = label
    report.overall_reliability_score = round(reliability, 4)
    report.decisions.append(
        f"confidence={label} overall={overall:.3f} "
        f"completeness={completeness.value} "
        f"coverage={question_coverage:.3f} grounding={grounding:.3f} "
        f"intent={intent_cov:.3f} specificity={specificity:.3f} "
        f"unsupported={unsupported_rate:.3f} reliability={reliability:.3f}"
    )
    return report
