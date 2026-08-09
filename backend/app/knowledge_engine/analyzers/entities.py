"""Entity extraction analyzer (regex + lexicon heuristics)."""

from __future__ import annotations

import re

from app.knowledge_engine.analyzers.base import AnalyzerContext
from app.knowledge_engine.enums import Department
from app.knowledge_engine.types import ExtractedEntities

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}\b"
)
_DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},\s+\d{4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.I,
)
_DOC_ID_RE = re.compile(
    r"\b(?:Document\s*ID|Doc(?:ument)?\s*#|Policy\s*ID)\s*[:#]?\s*([A-Z]{2,}[-/][A-Z0-9/-]+)\b"
    r"|\b([A-Z]{2,}-[A-Z]{2,}-\d{4}-\d{3,})\b"
)
_PROJECT_RE = re.compile(r"\bProject\s+([A-Z][A-Za-z0-9_-]+)\b")
_COMPANY_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&]+(?:\s+[A-Z][A-Za-z0-9&]+){0,3})\s+"
    r"(?:Corporation|Corp\.|Inc\.|Ltd\.|LLC|Company|Technologies)\b"
)
_POLICY_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9 /-]{2,60}?\sPolicy)\b"
)
_PERSON_RE = re.compile(
    r"\b(?:Owner|Author|Manager|Prepared by|Approved by)\s*:\s*"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b"
)

_TECHNOLOGIES = (
    "Slack", "Workday", "Okta", "VPN", "MFA", "Active Directory", "AWS", "Azure",
    "Kubernetes", "Docker", "Python", "FastAPI", "PostgreSQL", "FAISS",
)
_STANDARDS = ("GDPR", "SOC 2", "ISO 27001", "HIPAA", "PCI DSS", "SOX", "NIST")
_PRODUCTS = ("Knowra", "Workday HR", "Slack", "Okta")


def _unique(values: list[str], *, limit: int = 25) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


class EntityAnalyzer:
    name = "entities"

    def analyze(self, context: AnalyzerContext) -> None:
        text = context.request.text
        emails = _EMAIL_RE.findall(text)
        phones = _PHONE_RE.findall(text)
        dates = _DATE_RE.findall(text)
        doc_ids = [
            match.group(1) or match.group(2)
            for match in _DOC_ID_RE.finditer(text)
            if match.group(1) or match.group(2)
        ]
        projects = [match.group(1) for match in _PROJECT_RE.finditer(text)]
        companies = [match.group(1) for match in _COMPANY_RE.finditer(text)]
        # Also catch bare "ACME CORPORATION" style headers.
        companies.extend(
            match.group(0).title()
            for match in re.finditer(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,}){0,3}\s+CORPORATION\b", text)
        )
        policies = [match.group(1) for match in _POLICY_RE.finditer(text)]
        people = [match.group(1) for match in _PERSON_RE.finditer(text)]

        technologies = [tech for tech in _TECHNOLOGIES if re.search(rf"\b{re.escape(tech)}\b", text, re.I)]
        standards = [std for std in _STANDARDS if re.search(rf"\b{re.escape(std)}\b", text, re.I)]
        products = [product for product in _PRODUCTS if re.search(rf"\b{re.escape(product)}\b", text, re.I)]

        departments = [
            dept.value
            for dept in Department
            if dept not in {Department.UNKNOWN, Department.EXTERNAL, Department.PERSONAL}
            and re.search(rf"\b{re.escape(dept.value)}\b", text, re.I)
        ]
        departments.extend(context.knowledge.departments)

        locations = [
            match.group(0)
            for match in re.finditer(
                r"\b(?:New York|London|San Francisco|Berlin|Singapore|Remote|Headquarters)\b",
                text,
            )
        ]

        entities = ExtractedEntities(
            people=_unique(people),
            companies=_unique(companies),
            projects=_unique(projects),
            departments=_unique(departments),
            technologies=_unique(technologies),
            policies=_unique(policies),
            products=_unique(products),
            standards=_unique(standards),
            dates=_unique(dates),
            locations=_unique(locations),
            email=_unique(emails),
            phone=_unique(phones),
            document_ids=_unique(doc_ids),
        )
        context.knowledge.entities = entities
        context.knowledge.confidence.entities = (
            0.8 if entities.total_count() >= 3 else 0.55 if entities.total_count() else 0.2
        )
