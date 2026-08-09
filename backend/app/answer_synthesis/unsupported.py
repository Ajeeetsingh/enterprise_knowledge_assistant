"""Unsupported factual-request detection (Phase 4F).

Deterministic only. Does not call an LLM.
When the question asks for a specific fact that evidence does not contain,
synthesis recommends a clean refusal before generation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PERIOD_RE = re.compile(
    r"\b("
    r"q[1-4]\s*20\d{2}|"
    r"h[12]\s*20\d{2}|"
    r"fy\s*20\d{2}|"
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+20\d{2}|"
    r"20\d{2}\s*(?:q[1-4]|h[12])|"
    r"20(?:2[6-9]|[3-9]\d)"  # future-leaning years often absent from KB
    r")\b",
    re.I,
)

_FINANCIAL_METRIC_RE = re.compile(
    r"\b("
    r"profit|net income|earnings|revenue|ebitda|loss|financial results?|"
    r"quarterly results?|p&l|pnl|balance sheet"
    r")\b",
    re.I,
)

_SPECIFIC_FACT_RE = re.compile(
    r"\b("
    r"exact (?:number|figure|amount)|"
    r"how much (?:did|was|is)|"
    r"what was .+ (?:profit|revenue|income|earnings)"
    r")\b",
    re.I,
)


@dataclass(frozen=True)
class UnsupportedAssessment:
    is_unsupported: bool
    refusal_message: str | None
    unsupported_concepts: tuple[str, ...]
    reasons: tuple[str, ...]


def _normalize_period(match: str) -> str:
    return re.sub(r"\s+", " ", match.strip().upper())


def assess_unsupported_request(
    *,
    question: str,
    evidence_text: str,
) -> UnsupportedAssessment:
    """Return refusal guidance when evidence cannot support a specific fact ask."""
    q = question or ""
    evidence = evidence_text or ""
    evidence_l = evidence.lower()
    reasons: list[str] = []
    unsupported: list[str] = []

    period_match = _PERIOD_RE.search(q)
    wants_financial = bool(_FINANCIAL_METRIC_RE.search(q))
    wants_specific = bool(_SPECIFIC_FACT_RE.search(q)) or wants_financial

    if period_match and wants_financial:
        period = _normalize_period(period_match.group(0))
        period_l = period_match.group(0).lower()
        # Require the period (or close token) AND a financial metric in evidence.
        period_in_evidence = period_l in evidence_l or period.lower() in evidence_l
        # Also try compact forms like q22026
        compact = re.sub(r"\s+", "", period_l)
        period_in_evidence = period_in_evidence or compact in re.sub(r"\s+", "", evidence_l)
        metric_in_evidence = bool(_FINANCIAL_METRIC_RE.search(evidence))

        if not period_in_evidence or not metric_in_evidence:
            unsupported.append(f"financial_results:{period}")
            reasons.append("period_or_metric_absent_from_evidence")
            pretty_period = period_match.group(0).strip()
            msg = (
                "I couldn't find any document in the knowledge base that contains "
                f"Apex National Bank's {pretty_period} financial results."
            )
            # Prefer org-neutral phrasing if org name not in question.
            if "apex" not in q.lower():
                msg = (
                    "I couldn't find any document in the knowledge base that contains "
                    f"the requested {pretty_period} financial results."
                )
            return UnsupportedAssessment(
                is_unsupported=True,
                refusal_message=msg,
                unsupported_concepts=tuple(unsupported),
                reasons=tuple(reasons),
            )

    # Generic: specific numeric fact ask with no overlapping distinctive tokens.
    if wants_specific and period_match and not wants_financial:
        period_l = period_match.group(0).lower()
        if period_l not in evidence_l:
            unsupported.append(f"period_fact:{period_l}")
            reasons.append("requested_period_absent")
            return UnsupportedAssessment(
                is_unsupported=True,
                refusal_message=(
                    "I couldn't find any document in the knowledge base that contains "
                    f"information for {period_match.group(0).strip()}."
                ),
                unsupported_concepts=tuple(unsupported),
                reasons=tuple(reasons),
            )

    return UnsupportedAssessment(
        is_unsupported=False,
        refusal_message=None,
        unsupported_concepts=(),
        reasons=(),
    )
