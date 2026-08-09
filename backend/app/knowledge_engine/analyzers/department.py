"""Multi-label department classification analyzer."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.categorizer import resolve_category
from app.knowledge_engine.analyzers.base import AnalyzerContext
from app.knowledge_engine.enums import Department

_CATEGORY_TO_DEPARTMENT: dict[str, Department] = {
    "hr": Department.HR,
    "finance": Department.FINANCE,
    "security": Department.SECURITY,
    "employee": Department.HR,
    "general": Department.UNKNOWN,
}

_KEYWORD_RULES: list[tuple[Department, tuple[str, ...]]] = [
    (Department.HR, ("human resources", "hr policy", "hr department", "parental leave", "performance review", "employee handbook")),
    (Department.FINANCE, ("budget", "revenue report", "expense report", "fiscal year", "quarterly report", "accounting")),
    (Department.SECURITY, ("security policy", "mfa", "password policy", "incident response", "threat", "vulnerability")),
    (Department.IT, ("information technology", "it policy", "helpdesk", "service desk", "vpn access")),
    (Department.LEGAL, ("legal department", "legal counsel", "attorney", "non-disclosure", "regulatory compliance")),
    (Department.ENGINEERING, ("engineering team", "software engineering", "code review", "deployment pipeline")),
    (Department.MARKETING, ("marketing campaign", "brand guidelines", "go-to-market")),
    (Department.SALES, ("sales pipeline", "sales quota", "opportunity stage")),
    (Department.OPERATIONS, ("operations team", "on-call rotation", "service level agreement")),
    (Department.SUPPORT, ("customer support", "support ticket", "support team")),
    (Department.ADMIN, ("administration office", "admin policy", "office management")),
]


class DepartmentAnalyzer:
    name = "department"

    def analyze(self, context: AnalyzerContext) -> None:
        filename = context.request.filename
        text = context.request.text[:12000].lower()
        stem = Path(filename).stem.lower()
        scored: dict[Department, float] = {}

        category = resolve_category(filename)
        mapped = _CATEGORY_TO_DEPARTMENT.get(category)
        if mapped and mapped != Department.UNKNOWN:
            scored[mapped] = 0.9

        if context.request.department_hint:
            hint = context.request.department_hint.strip().lower()
            for dept in Department:
                if dept.value.lower() == hint:
                    scored[dept] = max(scored.get(dept, 0.0), 0.92)
                    break

        for dept, phrases in _KEYWORD_RULES:
            hits = sum(1 for phrase in phrases if phrase in text or phrase.replace(" ", "_") in stem)
            if hits == 0:
                continue
            # Require two distinct phrase hits before adding a secondary department.
            weight = 0.7 + 0.08 * hits if hits >= 2 else (0.55 if dept not in scored else 0.0)
            if weight > 0:
                scored[dept] = max(scored.get(dept, 0.0), min(0.93, weight))

        if not scored:
            context.knowledge.departments = [Department.UNKNOWN.value]
            context.knowledge.confidence.departments = 0.35
            return

        ranked = sorted(scored.items(), key=lambda item: item[1], reverse=True)
        # Keep the primary department plus at most one strong secondary label.
        selected = [ranked[0][0]]
        if len(ranked) > 1 and ranked[1][1] >= 0.7:
            selected.append(ranked[1][0])

        context.knowledge.departments = [dept.value for dept in selected]
        context.knowledge.confidence.departments = round(ranked[0][1], 3)
