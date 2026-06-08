"""Query routing to enterprise document categories."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RouteResult:
    """Result of query routing."""

    category: str
    confidence: float
    matched_keywords: list[str]


ROUTE_KEYWORDS: dict[str, list[str]] = {
    "employee": [
        "salary",
        "salaries",
        "employee record",
        "employee records",
        "employee id",
        "emp-",
        "personnel file",
        "compensation",
        "pay grade",
        "performance rating",
        "who works in",
        "headcount by name",
    ],
    "hr": [
        "parental leave",
        "sick leave",
        "remote work",
        "work from home",
        "performance review",
        "employee handbook",
        "hr policy",
        "annual leave",
        "leave policy",
        "onboarding",
        "promotion",
        "benefits",
        "insurance",
        "401k",
        "conduct",
        "harassment",
        "vacation",
        "pto",
        "manager",
        "leave",
    ],
    "finance": [
        "department spend",
        "headcount cost",
        "operating margin",
        "financial report",
        "quarter",
        "revenue",
        "expense",
        "profit",
        "budget",
        "forecast",
        "q1",
        "q2",
        "q3",
        "q4",
        "financial",
        "finance",
        "margin",
        "operating",
        "audit",
        "investment",
        "growth",
        "earnings",
    ],
    "security": [
        "multi factor authentication",
        "multi-factor authentication",
        "security incident",
        "password policy",
        "password requirements",
        "failed login",
        "access control",
        "authentication",
        "password",
        "malware",
        "exfiltration",
        "quarantine",
        "intrusion",
        "vulnerability",
        "privilege",
        "firewall",
        "incident",
        "security",
        "breach",
        "threat",
        "mfa",
        "login",
        "siem",
        "patch",
        "vpn",
        "dlp",
        "log",
    ],
}

# Higher value wins tie-breaks when scores are equal.
CATEGORY_PRIORITY = {
    "security": 4,
    "employee": 3,
    "finance": 2,
    "hr": 1,
}

DEFAULT_CATEGORY = "hr"
DEFAULT_CONFIDENCE = 0.3


def _normalize_query(query: str) -> str:
    """Normalize query text for keyword matching."""
    normalized = query.lower().strip()
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _score_category(query_lower: str, keywords: list[str]) -> tuple[float, list[str]]:
    """Score a category using longest-keyword-first matching."""
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    hits: list[str] = []
    score = 0.0

    for keyword in sorted_keywords:
        if keyword in query_lower:
            hits.append(keyword)
            score += len(keyword.split())

    return score, hits


def route_query(query: str) -> RouteResult:
    """
    Route a user query to hr, finance, security, or employee.

    Uses weighted keyword scoring with longest-match preference.
    Security keywords take priority on ties.
    """
    query_lower = _normalize_query(query)
    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}

    for category, keywords in ROUTE_KEYWORDS.items():
        score, hits = _score_category(query_lower, keywords)
        if hits:
            scores[category] = score
            matched[category] = hits

    if not scores:
        return RouteResult(
            category=DEFAULT_CATEGORY,
            confidence=DEFAULT_CONFIDENCE,
            matched_keywords=[],
        )

    best_category = max(
        scores,
        key=lambda category: (scores[category], CATEGORY_PRIORITY[category]),
    )
    best_score = scores[best_category]
    total_score = sum(scores.values())
    confidence = round(best_score / total_score, 3) if total_score > 0 else DEFAULT_CONFIDENCE

    return RouteResult(
        category=best_category,
        confidence=confidence,
        matched_keywords=matched[best_category],
    )


def route_to_categories(query: str) -> list[str]:
    """Return ordered list of categories to search (primary first)."""
    result = route_query(query)
    categories = [result.category]

    for category in ("hr", "finance", "security", "employee"):
        if category not in categories:
            categories.append(category)

    return categories
