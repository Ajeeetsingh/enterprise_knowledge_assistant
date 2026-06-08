"""Document category resolution from filenames."""

from __future__ import annotations

from pathlib import Path

CATEGORY_MAP: dict[str, str] = {
    "hr_policy": "hr",
    "employee_handbook": "hr",
    "leave_policies": "hr",
    "remote_work_policy": "hr",
    "performance_review_policy": "hr",
    "finance_report": "finance",
    "quarterly_reports": "finance",
    "department_budgets": "finance",
    "revenue_reports": "finance",
    "expense_reports": "finance",
    "security_logs": "security",
    "security_policy": "security",
    "mfa_policy": "security",
    "password_policy": "security",
    "incident_response": "security",
    "employees": "employee",
    "it_security_policy": "security",
}


def resolve_category(filename: str) -> str:
    """Map a filename stem to a document category."""
    stem = Path(filename).stem
    return CATEGORY_MAP.get(stem, "general")
