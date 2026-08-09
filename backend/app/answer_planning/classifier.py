"""Deterministic answer-type classification (no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.answer_planning.enums import AnswerType

# Ordered rules: first match wins. Patterns are tested against lowered text.
_RULES: tuple[tuple[AnswerType, tuple[str, ...], re.Pattern[str]], ...] = (
    (
        AnswerType.COMPARISON,
        ("compare/contrast language",),
        re.compile(
            r"\b(compare|comparison|contrast|difference|differences|vs\.?|versus|"
            r"similarit(?:y|ies)|differ from)\b",
            re.I,
        ),
    ),
    (
        AnswerType.WORKFLOW,
        ("workflow/journey/process language",),
        re.compile(
            r"\b(journey|end[- ]to[- ]end|from\b.+\bto\b|workflow|process flow|"
            r"step[- ]by[- ]step|ordered steps|complete (?:process|governance)|"
            r"lifecycle|stages of)\b"
            r"|\bdescribe the complete\b",
            re.I,
        ),
    ),
    (
        AnswerType.RELATIONSHIP,
        ("relationship / work-together language",),
        re.compile(
            r"\b(work together|relate|relationship|relationships|interact|"
            r"interrelate|connected|how .+ supports?|hierarchy .+ support|"
            r"link between|connection between)\b",
            re.I,
        ),
    ),
    (
        AnswerType.SUMMARY,
        ("summary language",),
        re.compile(
            r"\b(summarize|summary|overview of|high[- ]level overview|brief overview)\b",
            re.I,
        ),
    ),
    (
        AnswerType.DECISION_GUIDANCE,
        ("decision / approval authority language",),
        re.compile(
            r"\b(which (?:committee|body|authority|role|person)|who should|"
            r"should approve|who (?:approves|owns)|"
            r"recommend(?:ed)? (?:committee|approver|path)|which .+ should|"
            r"approval path)\b",
            re.I,
        ),
    ),
    (
        AnswerType.LIST_EXTRACTION,
        ("list / categories language",),
        re.compile(
            r"\b(what are (?:the )?(?:different )?(?:categories|types|kinds|levels|"
            r"values|components|elements|items)|list (?:the|all)|"
            r"categories of|types of|enumerate|"
            r"connections must|must every .{0,40} declare)\b",
            re.I,
        ),
    ),
    (
        AnswerType.TROUBLESHOOTING,
        ("troubleshooting language",),
        re.compile(
            r"\b(troubleshoot|troubleshooting|why (?:is|does|did|can.?t|won.?t)|"
            r"not working|error|issue|fix|root cause|diagnos)\b",
            re.I,
        ),
    ),
    (
        AnswerType.COMPLIANCE,
        ("compliance / regulatory language",),
        re.compile(
            r"\b(complian(?:ce|t)|regulatory|regulation|obligation|obligations|"
            r"must comply|control requirement|audit (?:requirement|evidence))\b",
            re.I,
        ),
    ),
    (
        AnswerType.POLICY_LOOKUP,
        ("policy requirements language",),
        re.compile(
            r"\b(policy)\b.+\b(require|requirement|scope|exception|apply|applies|"
            r"must|shall|retention period|allowed|prohibited)\b"
            r"|\b(requirements|scope|exceptions) of (?:the )?.+\bpolicy\b"
            r"|\baccording to (?:the )?.+\bpolicy\b",
            re.I,
        ),
    ),
    (
        AnswerType.GOVERNANCE,
        ("governance structure language",),
        re.compile(
            r"\b(governance|committee charter|oversight|mandate|board|"
            r"delegated authority|enterprise committee)\b",
            re.I,
        ),
    ),
    (
        AnswerType.REFERENCE_LOOKUP,
        ("reference / identifier language",),
        re.compile(
            r"\b(document id|doc(?:ument)? code|filename|file name|"
            r"where (?:is|can i find)|which document|reference (?:id|number)|"
            r"identifier format)\b",
            re.I,
        ),
    ),
    (
        AnswerType.DEFINITION,
        ("definition language",),
        re.compile(
            r"\b(what is|what'?s|define|definition of|meaning of)\b",
            re.I,
        ),
    ),
    (
        AnswerType.EXPLANATION,
        ("explanation language",),
        re.compile(
            r"\b(explain|describe|how (?:does|do|is|are)|walk me through|"
            r"tell me how)\b",
            re.I,
        ),
    ),
)


@dataclass(frozen=True)
class ClassificationDecision:
    """Raw classifier output before blueprint attachment."""

    answer_type: AnswerType
    reason: str
    matched_signals: tuple[str, ...]


def classify_answer_type(question: str) -> ClassificationDecision:
    """Classify how an answer should be structured.

    Deterministic, tenant-agnostic, and independent of retrieval classification.
    """
    text = " ".join((question or "").strip().split())
    if not text:
        return ClassificationDecision(
            answer_type=AnswerType.EXPLANATION,
            reason="Empty question; defaulted to Explanation",
            matched_signals=("default",),
        )

    lowered = text.lower()
    for answer_type, signal_labels, pattern in _RULES:
        match = pattern.search(lowered)
        if match:
            token = match.group(0).strip()
            reason = (
                f"Matched {answer_type.value} signals: "
                f"{', '.join(signal_labels)} (hit={token!r})"
            )
            return ClassificationDecision(
                answer_type=answer_type,
                reason=reason,
                matched_signals=(token, *signal_labels),
            )

    return ClassificationDecision(
        answer_type=AnswerType.EXPLANATION,
        reason="No specific structure signals; defaulted to Explanation",
        matched_signals=("default",),
    )
