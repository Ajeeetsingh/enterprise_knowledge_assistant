"""Rule-based query classification."""

from __future__ import annotations

import re

from app.rag.query_processing.schemas import ClassificationResult, QueryCategory

_CROSS_DOC_PATTERNS = (
    re.compile(r"\brelated\b.+\bdocument\b", re.I),
    re.compile(r"\breferenced\b", re.I),
    re.compile(r"\bcross[\s-]?reference\b", re.I),
    re.compile(r"\bwhich document\b", re.I),
    re.compile(r"\bother\b.+\bpolicy\b", re.I),
)

_COMPLIANCE_PATTERNS = (
    re.compile(r"\baml\b", re.I),
    re.compile(r"\bkyc\b", re.I),
    re.compile(r"\bcompliance\b", re.I),
    re.compile(r"\bregulat", re.I),
    re.compile(r"\banti[\s-]?money\b", re.I),
)

_SECURITY_PATTERNS = (
    re.compile(r"\bsecurity\b", re.I),
    re.compile(r"\bcyber\b", re.I),
    re.compile(r"\bvpn\b", re.I),
    re.compile(r"\bmfa\b", re.I),
    re.compile(r"\bpassword\b", re.I),
    re.compile(r"\baccess control\b", re.I),
)

_FINANCIAL_PATTERNS = (
    re.compile(r"\brevenue\b", re.I),
    re.compile(r"\bbudget\b", re.I),
    re.compile(r"\bfinancial\b", re.I),
    re.compile(r"\bquarterly\b", re.I),
    re.compile(r"\bearnings\b", re.I),
    re.compile(r"\bprofit\b", re.I),
    re.compile(r"\bfiscal\b", re.I),
)

_POLICY_PATTERNS = (
    re.compile(r"\bpolicy\b", re.I),
    re.compile(r"\bguideline\b", re.I),
    re.compile(r"\bstandard\b", re.I),
    re.compile(r"\bhandbook\b", re.I),
)

_PROCEDURE_PATTERNS = (
    re.compile(r"\bprocedure\b", re.I),
    re.compile(r"\bprocess\b", re.I),
    re.compile(r"\bworkflow\b", re.I),
    re.compile(r"\bsop\b", re.I),
    re.compile(r"\bstep\b", re.I),
    re.compile(r"\bapproval\b", re.I),
)

_COMPARISON_PATTERNS = (
    re.compile(r"\bcompare\b", re.I),
    re.compile(r"\bcomparison\b", re.I),
    re.compile(r"\bversus\b", re.I),
    re.compile(r"\bvs\.?\b", re.I),
    re.compile(r"\bdifference\b", re.I),
)

_TABLE_PATTERNS = (
    re.compile(r"\btable\b", re.I),
    re.compile(r"\bmatrix\b", re.I),
    re.compile(r"\bbreakdown\b", re.I),
)

_LIST_PATTERNS = (
    re.compile(r"^\s*list\b", re.I),
    re.compile(r"\bwhat are the\b", re.I),
    re.compile(r"\bwhich\b.+\bare\b", re.I),
    re.compile(r"\benumerate\b", re.I),
)

_NUMERIC_PATTERNS = (
    re.compile(r"\bhow many\b", re.I),
    re.compile(r"\bhow much\b", re.I),
    re.compile(r"\btotal\b", re.I),
    re.compile(r"\bcount\b", re.I),
    re.compile(r"\bpercentage\b", re.I),
    re.compile(r"\bpercent\b", re.I),
)

_DEFINITION_PATTERNS = (
    re.compile(r"^\s*what is\b", re.I),
    re.compile(r"^\s*what are\b", re.I),
    re.compile(r"^\s*define\b", re.I),
    re.compile(r"^\s*explain\b", re.I),
)

_ENTITY_PATTERNS = (
    re.compile(r"^\s*who is\b", re.I),
    re.compile(r"^\s*where is\b", re.I),
    re.compile(r"\bheadquarters\b", re.I),
    re.compile(r"\bceo\b", re.I),
    re.compile(r"\bcto\b", re.I),
    re.compile(r"\bcfo\b", re.I),
    re.compile(r"\bexecutive\b", re.I),
    re.compile(r"\blocated\b", re.I),
)


def classify_query(query: str) -> ClassificationResult:
    """Classify a query using deterministic keyword rules."""
    normalized = query.strip()
    if not normalized:
        return ClassificationResult(QueryCategory.GENERAL, 0.5, ("empty_query",))

    checks: list[tuple[QueryCategory, tuple[re.Pattern[str], ...], float]] = [
        (QueryCategory.CROSS_DOCUMENT, _CROSS_DOC_PATTERNS, 0.88),
        (QueryCategory.COMPLIANCE, _COMPLIANCE_PATTERNS, 0.86),
        (QueryCategory.SECURITY, _SECURITY_PATTERNS, 0.84),
        (QueryCategory.FINANCIAL, _FINANCIAL_PATTERNS, 0.84),
        (QueryCategory.TABLE, _TABLE_PATTERNS, 0.83),
        (QueryCategory.COMPARISON, _COMPARISON_PATTERNS, 0.82),
        (QueryCategory.LIST, _LIST_PATTERNS, 0.81),
        (QueryCategory.NUMERIC, _NUMERIC_PATTERNS, 0.8),
        (QueryCategory.PROCEDURE, _PROCEDURE_PATTERNS, 0.78),
        (QueryCategory.POLICY, _POLICY_PATTERNS, 0.77),
        (QueryCategory.ENTITY_LOOKUP, _ENTITY_PATTERNS, 0.76),
        (QueryCategory.DEFINITION, _DEFINITION_PATTERNS, 0.74),
    ]

    for category, patterns, confidence in checks:
        matched = [pattern.pattern for pattern in patterns if pattern.search(normalized)]
        if matched:
            return ClassificationResult(
                category=category,
                confidence=confidence,
                signals=tuple(matched[:3]),
            )

    return ClassificationResult(QueryCategory.GENERAL, 0.55, ("default",))
