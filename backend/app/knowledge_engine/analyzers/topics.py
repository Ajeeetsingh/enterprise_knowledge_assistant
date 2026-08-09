"""Topic detection analyzer."""

from __future__ import annotations

import re

from app.knowledge_engine.analyzers.base import AnalyzerContext
from app.knowledge_engine.text_utils import significant_tokens, top_keywords

_TOPIC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Annual Leave", re.compile(r"\b(annual leave|paid leave|time off|pto)\b", re.I)),
    ("Remote Work", re.compile(r"\b(remote work|hybrid work|work from home|wfh)\b", re.I)),
    ("Parental Leave", re.compile(r"\b(parental leave|maternity|paternity)\b", re.I)),
    ("Performance Management", re.compile(r"\b(performance review|performance management)\b", re.I)),
    ("Access Control", re.compile(r"\b(access control|least privilege|authorization)\b", re.I)),
    ("Multi-Factor Authentication", re.compile(r"\b(mfa|multi[- ]factor|2fa)\b", re.I)),
    ("Incident Response", re.compile(r"\b(incident response|security incident|breach)\b", re.I)),
    ("Password Security", re.compile(r"\b(password|passphrase|credential)\b", re.I)),
    ("Budgeting", re.compile(r"\b(budget|forecast|allocation)\b", re.I)),
    ("Revenue", re.compile(r"\b(revenue|arr|mrr|sales)\b", re.I)),
    ("Expenses", re.compile(r"\b(expense|reimbursement|cost center)\b", re.I)),
    ("Compliance", re.compile(r"\b(compliance|audit|regulatory|gdpr|sox)\b", re.I)),
]


class TopicAnalyzer:
    name = "topics"

    def analyze(self, context: AnalyzerContext) -> None:
        text = context.request.text
        topics: list[str] = []
        for label, pattern in _TOPIC_PATTERNS:
            if pattern.search(text):
                topics.append(label)

        if len(topics) < 3:
            for keyword in top_keywords(text, limit=8):
                candidate = keyword.replace("_", " ").title()
                if candidate not in topics and len(significant_tokens(candidate)) >= 1:
                    topics.append(candidate)
                if len(topics) >= 8:
                    break

        context.knowledge.topics = topics[:10]
        context.knowledge.confidence.topics = 0.78 if topics else 0.3
