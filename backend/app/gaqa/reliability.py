"""Reliability finalization — honest refusals / partial notes (Phase 4E).

May recommend replacing the returned answer only for reliability outcomes.
Does not invent enterprise facts. GAQA itself does not mutate the answer string.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from app.gaqa.intent import IntentAssessment
from app.gaqa.types import GaqaReport

_DOC_PREFIX_RE = re.compile(
    r"(?im)^(?:according to|per|from)\s+[A-Za-z0-9_\-]+\.pdf[:\s,-]*"
    r"|^[A-Za-z0-9_\-]+\.pdf\s+(?:states?|says?|notes?|explains?|describes?)\s+that\s+"
)


class AnswerCompleteness(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    RELATED_NOT_ANSWERING = "related_not_answering"
    NO_EVIDENCE = "no_evidence"
    EXPLICIT_REFUSAL = "explicit_refusal"


@dataclass(frozen=True)
class ReliabilityDecision:
    completeness: AnswerCompleteness
    refusal_reason: str | None
    final_answer: str | None  # None => keep generated answer
    notes: tuple[str, ...]


def _soft_integrate_document_enumeration(answer: str) -> str:
    """Remove repeated document-attribution prefixes; keep factual sentences."""
    text = (answer or "").strip()
    if not text:
        return text
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        cleaned = _DOC_PREFIX_RE.sub("", line).strip()
        cleaned_lines.append(cleaned if cleaned else line)
    merged = "\n".join(cleaned_lines)
    return re.sub(r"\n{3,}", "\n\n", merged).strip()


def decide_reliability(
    *,
    question: str,
    answer: str,
    report: GaqaReport,
    intent: IntentAssessment,
    has_results: bool,
) -> ReliabilityDecision:
    """Choose completeness class and optional final answer override."""
    notes: list[str] = []
    missing = list(report.missing_concepts)
    missing_in_evidence = [
        item.concept
        for item in report.question_coverage
        if (not item.present_in_answer) and (not item.present_in_evidence)
    ]
    answered_concepts = [
        item.concept for item in report.question_coverage if item.present_in_answer
    ]

    if not has_results:
        return ReliabilityDecision(
            completeness=AnswerCompleteness.NO_EVIDENCE,
            refusal_reason="no_retrieved_evidence",
            final_answer=(
                "I couldn't find any document in the knowledge base that answers "
                "this question."
            ),
            notes=("no_results",),
        )

    if intent.explicit_refusal:
        if not intent.intent_covered:
            return ReliabilityDecision(
                completeness=AnswerCompleteness.EXPLICIT_REFUSAL,
                refusal_reason="model_refusal_intent_uncovered",
                final_answer=_related_not_answering_message(question, intent),
                notes=("explicit_refusal", "intent_uncovered"),
            )
        return ReliabilityDecision(
            completeness=AnswerCompleteness.EXPLICIT_REFUSAL,
            refusal_reason="model_refusal",
            final_answer=None,
            notes=("explicit_refusal",),
        )

    # Related docs exist but do not cover the asked intent.
    if not intent.intent_covered:
        return ReliabilityDecision(
            completeness=AnswerCompleteness.RELATED_NOT_ANSWERING,
            refusal_reason="intent_not_covered_by_evidence",
            final_answer=_related_not_answering_message(question, intent),
            notes=tuple(intent.reasons) + ("intent_uncovered",),
        )

    # Partial: some requested concepts answered, some absent.
    if missing and answered_concepts:
        unsupported_missing = missing_in_evidence or missing
        partial = _partial_answer_message(
            answer=answer,
            supported=answered_concepts,
            missing=unsupported_missing,
        )
        notes.append("partial_concepts")
        final = partial
        if intent.multi_document_enumeration:
            final = _soft_integrate_document_enumeration(final)
            notes.append("soft_integrated_enumeration")
        return ReliabilityDecision(
            completeness=AnswerCompleteness.PARTIAL,
            refusal_reason=None,
            final_answer=final,
            notes=tuple(notes),
        )

    final_answer = None
    if intent.multi_document_enumeration:
        integrated = _soft_integrate_document_enumeration(answer)
        if integrated != (answer or "").strip():
            final_answer = integrated
            notes.append("soft_integrated_enumeration")

    if missing and not answered_concepts:
        return ReliabilityDecision(
            completeness=AnswerCompleteness.RELATED_NOT_ANSWERING,
            refusal_reason="requested_concepts_absent",
            final_answer=_related_not_answering_message(question, intent),
            notes=("concepts_absent",),
        )

    return ReliabilityDecision(
        completeness=AnswerCompleteness.COMPLETE,
        refusal_reason=None,
        final_answer=final_answer,
        notes=tuple(notes) if notes else ("complete",),
    )


def _related_not_answering_message(question: str, intent: IntentAssessment) -> str:
    subject = ""
    if intent.subject_markers:
        pretty = {
            "chatgpt": "employees using ChatGPT or similar AI assistants",
            "personal_ai": "employees using personal AI assistants",
            "salary": "employee salary or compensation",
            "vpn": "VPN or remote-access usage",
            "password": "password or credential handling",
            "leave": "employee leave entitlements",
            "crypto": "cryptocurrency activity",
        }
        labels = [pretty.get(m, m.replace("_", " ")) for m in intent.subject_markers]
        subject = labels[0]
    elif intent.intent_terms:
        subject = " / ".join(intent.intent_terms[:4])

    if subject:
        return (
            "I couldn't find any document in the knowledge base that defines "
            f"this for {subject}. Related governance or enterprise documents were "
            "retrieved, but they do not answer this specific question."
        )
    return (
        "I couldn't find any document in the knowledge base that answers this question. "
        "Related documents were retrieved, but they do not cover the requested topic."
    )


def _partial_answer_message(
    *,
    answer: str,
    supported: list[str],
    missing: list[str],
) -> str:
    body = (answer or "").strip()
    supported_txt = ", ".join(supported)
    missing_txt = ", ".join(missing)
    note = (
        f"I found information about {supported_txt}, but I could not find any document "
        f"describing {missing_txt}."
    )
    if note.lower() in body.lower():
        return body
    if not body:
        return note
    return f"{body}\n\n{note}"
