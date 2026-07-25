"""Lightweight high-confidence unsafe-intent detection.

Does NOT block legitimate enterprise policy questions that mention sensitive
topics (harassment, drugs, workplace violence, etc.). Focuses on clearly
harmful user intent rather than isolated keywords.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Enterprise policy / procedure framing — these must stay routable to RAG.
_LEGITIMATE_POLICY_FRAME = re.compile(
    r"\b("
    r"policy|policies|procedure|procedures|handbook|guideline|guidelines|"
    r"training|code\s+of\s+conduct|what\s+does\s+our|"
    r"what\s+is\s+our|according\s+to\s+(?:the|our)|"
    r"workplace\s+(?:harassment|violence|safety)|"
    r"employee\s+(?:drug|conduct|safety)"
    r")\b",
    re.I,
)

# High-confidence harmful-intent patterns (verbs + clearly illicit goals).
_HARMFUL_INTENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bhow\s+(?:do|can|to|would)\s+(?:i|we|you)\s+"
        r"(?:make|build|create|assemble)\s+(?:a\s+)?(?:bomb|explosive|pipe\s*bomb)\b",
        re.I,
    ),
    re.compile(
        r"\bhow\s+(?:do|can|to)\s+(?:i|we)\s+"
        r"(?:poison|murder|assassinate)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:write|give|show)\s+(?:me\s+)?(?:detailed\s+)?"
        r"(?:instructions|steps)\s+(?:for|on)\s+"
        r"(?:making|building)\s+(?:a\s+)?(?:bomb|explosive|weapon)\b",
        re.I,
    ),
    re.compile(
        r"\bhow\s+(?:do|can|to)\s+(?:i|we)\s+"
        r"(?:hack|break\s+into)\s+(?:someone(?:'s)?|a\s+stranger(?:'s)?)\s+"
        r"(?:email|bank|account|wifi|phone)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:child\s*porn|csam|underage\s+sex(?:ual)?\s+(?:content|images|photos))\b",
        re.I,
    ),
    re.compile(
        r"\bhow\s+(?:do|can|to)\s+(?:i|we)\s+"
        r"(?:cover\s+up|hide)\s+(?:a\s+)?(?:murder|crime|assault)\b",
        re.I,
    ),
)


UNSAFE_BOUNDARY_MESSAGE = (
    "I can't help with that request. "
    "If you're looking for your organization's workplace policies or safety "
    "procedures, ask about those documents and I'll help within your access permissions."
)


@dataclass(frozen=True)
class SafetyDecision:
    """Outcome of lightweight unsafe-intent screening."""

    is_unsafe: bool
    confidence: float
    method: str
    signals: tuple[str, ...] = ()


def assess_unsafe_intent(query: str) -> SafetyDecision:
    """Return whether *query* is a high-confidence clearly unsafe request.

    Legitimate enterprise questions about sensitive policy topics are allowed
    through (``is_unsafe=False``) so they can reach DOCUMENT_QUERY / RAG.
    """
    text = query.strip()
    if not text:
        return SafetyDecision(False, 0.0, "empty")

    # Policy / procedure framing about sensitive workplace topics is legitimate.
    if _LEGITIMATE_POLICY_FRAME.search(text):
        return SafetyDecision(
            False,
            0.9,
            "legitimate_policy_frame",
            ("policy_or_procedure_framing",),
        )

    for pattern in _HARMFUL_INTENT_PATTERNS:
        if pattern.search(text):
            return SafetyDecision(
                True,
                0.95,
                "harmful_intent_pattern",
                (pattern.pattern,),
            )

    return SafetyDecision(False, 0.0, "clear")
