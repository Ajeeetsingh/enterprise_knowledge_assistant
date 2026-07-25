"""Deterministic DOCUMENT vs GENERAL knowledge-route signals.

Cost-conscious first pass used by ``KnowledgeRouteClassifier`` before any
optional LLM classification. Reuses ``classify_query`` categories as hints
only — they alone do not decide DOCUMENT vs GENERAL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.query_processing.classifier import classify_query
from app.rag.query_processing.schemas import QueryCategory

# Strong organization / document grounding cues.
_ORG_POSSESSIVE = re.compile(
    r"\b("
    r"our|ours|"
    r"my\s+company(?:'s)?|the\s+company(?:'s)?|company(?:'s)?|"
    r"organisation(?:'s)?|organization(?:'s)?|"
    r"this\s+(?:company|organisation|organization|firm)|"
    r"internal"
    r")\b",
    re.I,
)

_DOC_REFERENCE = re.compile(
    r"\b("
    r"according\s+to|"
    r"per\s+the|"
    r"in\s+the\s+(?:handbook|policy|document|report|filing)|"
    r"uploaded\s+documents?|"
    r"the\s+document\s+says|"
    r"what\s+does\s+(?:the|our)\s+.+\s+(?:say|state|specify)|"
    r"knowledge\s+base|"
    r"source\s+document"
    r")\b",
    re.I,
)

_SUMMARIZE_ORG_DOC = re.compile(
    r"\b(summarize|summarise|summary\s+of)\b.+\b("
    r"policy|policies|report|handbook|document|filing|q[1-4]|quarter"
    r")\b",
    re.I,
)

_ORG_PERFORMANCE = re.compile(
    r"\b(our|company(?:'s)?)\b.+\b("
    r"revenue|earnings|budget|performance|profit|liquidity|"
    r"q[1-4]|quarter(?:ly)?|fiscal"
    r")\b",
    re.I,
)

_THE_POLICY = re.compile(
    r"\bthe\s+(?:\w+\s+){0,3}(policy|policies|procedure|handbook|guidelines?)\b",
    re.I,
)

# Strong general-knowledge / chit-chat cues.
_GREETING = re.compile(
    r"^\s*(hi|hello|hey|howdy|good\s+(morning|afternoon|evening))"
    r"(?:\s*[,!]?\s*(?:there|again|everyone|team|all|"
    r"how\s+are\s+you(?:\s+doing)?|how'?s\s+it\s+going|"
    r"what'?s\s+up)?)?"
    r"[!?.\s]*$",
    re.I,
)
_THANKS = re.compile(
    r"^\s*(thanks|thank\s+you|thx|cheers)[!?.\s]*$",
    re.I,
)

_WRITE_HELP = re.compile(
    r"\b("
    r"help\s+me\s+write|help\s+me\s+draft|help\s+me\s+compose|"
    r"draft\s+a|write\s+a|compose\s+a|create\s+a\s+(?:professional\s+)?"
    r"(?:email|agenda|outline|summary|letter|memo)"
    r")\b",
    re.I,
)

_PURE_DEFINITION = re.compile(
    r"^\s*(what\s+is|what\s+are|what'?s|define|explain|describe)\b",
    re.I,
)

_DIFFERENCE_GENERAL = re.compile(
    r"\b(difference\s+between|versus|vs\.?)\b",
    re.I,
)

_ORG_DOC_CATEGORIES = frozenset(
    {
        QueryCategory.POLICY,
        QueryCategory.PROCEDURE,
        QueryCategory.COMPLIANCE,
        QueryCategory.SECURITY,
        QueryCategory.FINANCIAL,
        QueryCategory.CROSS_DOCUMENT,
    }
)


@dataclass(frozen=True)
class SignalScore:
    """Aggregated heuristic score for one knowledge route."""

    score: float
    signals: tuple[str, ...]


def score_document_signals(query: str) -> SignalScore:
    """Return how strongly *query* looks organization/document-specific."""
    text = query.strip()
    if not text:
        return SignalScore(0.0, ("empty",))

    signals: list[str] = []
    score = 0.0

    if _ORG_POSSESSIVE.search(text):
        signals.append("org_possessive")
        score = max(score, 0.92)
    if _DOC_REFERENCE.search(text):
        signals.append("document_reference")
        score = max(score, 0.9)
    if _SUMMARIZE_ORG_DOC.search(text):
        signals.append("summarize_org_document")
        score = max(score, 0.88)
    if _ORG_PERFORMANCE.search(text):
        signals.append("org_performance")
        score = max(score, 0.9)
    if _THE_POLICY.search(text) and _ORG_POSSESSIVE.search(text):
        signals.append("possessive_policy")
        score = max(score, 0.93)
    elif _THE_POLICY.search(text):
        signals.append("the_policy_phrase")
        score = max(score, 0.62)

    classification = classify_query(text)
    if classification.category in _ORG_DOC_CATEGORIES and _ORG_POSSESSIVE.search(text):
        signals.append(f"category:{classification.category.value}+org")
        score = max(score, 0.9)
    elif (
        classification.category in _ORG_DOC_CATEGORIES
        and not _ORG_POSSESSIVE.search(text)
        and not _PURE_DEFINITION.match(text)
    ):
        # e.g. "List AML requirements" — lean document unless clearly definitional.
        signals.append(f"category:{classification.category.value}")
        score = max(score, 0.58)

    return SignalScore(score=score, signals=tuple(signals) or ("none",))


def score_general_signals(query: str) -> SignalScore:
    """Return how strongly *query* looks like general knowledge / chit-chat."""
    text = query.strip()
    if not text:
        return SignalScore(0.0, ("empty",))

    # Organization-specific cues veto general classification.
    if _ORG_POSSESSIVE.search(text) or _DOC_REFERENCE.search(text) or _ORG_PERFORMANCE.search(text):
        return SignalScore(0.0, ("blocked_by_org_signal",))

    signals: list[str] = []
    score = 0.0

    if _GREETING.match(text) or _THANKS.match(text):
        signals.append("greeting")
        score = max(score, 0.95)
    if _WRITE_HELP.search(text):
        signals.append("writing_help")
        score = max(score, 0.9)

    classification = classify_query(text)
    if _PURE_DEFINITION.match(text) and classification.category in {
        QueryCategory.DEFINITION,
        QueryCategory.GENERAL,
        QueryCategory.COMPARISON,
    }:
        signals.append("definition_without_org")
        score = max(score, 0.82)
    if _DIFFERENCE_GENERAL.search(text) and not _ORG_POSSESSIVE.search(text):
        # "difference between revenue and profit" — conceptual, not "our revenue".
        if not re.search(r"\b(our|company(?:'s)?)\b", text, re.I):
            signals.append("general_comparison")
            score = max(score, 0.8)

    # Short chit-chat / acknowledgements
    if len(text.split()) <= 3 and re.match(
        r"^\s*(hi|hello|hey|thanks|ok|okay|cool|great)[!?.\s]*$",
        text,
        re.I,
    ):
        signals.append("short_chitchat")
        score = max(score, 0.9)

    return SignalScore(score=score, signals=tuple(signals) or ("none",))
