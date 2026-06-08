"""Realistic enterprise test suite for the ACME RAG system.

Simulates a full company knowledge base with HR, finance, security,
and employee data. Validates routing, RBAC, retrieval sources, and answers.

Usage:
    python realistic_enterprise_test.py
"""

from __future__ import annotations

import json
import sys
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.rag.engine import EnterpriseRAG
from app.ingestion.loader import load_documents
from app.rag.rbac import check_access
from app.rag.router import route_query

REPO_ROOT = BACKEND_ROOT.parent
DATA_DIR = BACKEND_ROOT / "tests" / "fixtures" / "sample_docs"
RESULTS_DIR = REPO_ROOT / "results"
RESULTS_JSON = RESULTS_DIR / "realistic_test_results.json"
RESULTS_TXT = RESULTS_DIR / "realistic_test_results.txt"
REPORT_MD = RESULTS_DIR / "realistic_test_report.md"

ENTERPRISE_DATASETS = [
    "employee_handbook.txt",
    "leave_policies.txt",
    "remote_work_policy.txt",
    "performance_review_policy.txt",
    "quarterly_reports.txt",
    "department_budgets.txt",
    "revenue_reports.txt",
    "expense_reports.txt",
    "security_policy.txt",
    "mfa_policy.txt",
    "password_policy.txt",
    "incident_response.txt",
    "security_logs.json",
    "employees.csv",
    "hr_policy.txt",
    "finance_report.txt",
    "it_security_policy.pdf",
]

TEST_CASES = [
    # HR
    {
        "id": "HR-01",
        "category": "HR",
        "query": "What is the maternity leave policy?",
        "role": "employee",
        "expected_route": "hr",
        "expected_access": True,
        "expected_sources": ["leave_policies.txt", "hr_policy.txt"],
        "answer_keywords": ["16 weeks", "primary"],
    },
    {
        "id": "HR-02",
        "category": "HR",
        "query": "Can employees work remotely?",
        "role": "employee",
        "expected_route": "hr",
        "expected_access": True,
        "expected_sources": ["remote_work_policy.txt", "hr_policy.txt"],
        "answer_keywords": ["remote", "3 days"],
    },
    {
        "id": "HR-03",
        "category": "HR",
        "query": "How often are performance reviews conducted?",
        "role": "employee",
        "expected_route": "hr",
        "expected_access": True,
        "expected_sources": ["performance_review_policy.txt", "hr_policy.txt"],
        "answer_keywords": ["q4", "performance reviews"],
    },
    {
        "id": "HR-04",
        "category": "HR",
        "query": "What is the employee handbook code of conduct?",
        "role": "hr",
        "expected_route": "hr",
        "expected_access": True,
        "expected_sources": ["employee_handbook.txt", "hr_policy.txt"],
        "answer_keywords": ["conduct", "handbook"],
    },
    {
        "id": "HR-05",
        "category": "HR",
        "query": "How many sick days do employees receive?",
        "role": "employee",
        "expected_route": "hr",
        "expected_access": True,
        "expected_sources": ["leave_policies.txt", "hr_policy.txt"],
        "answer_keywords": ["10", "sick"],
    },
    {
        "id": "HR-06",
        "category": "HR",
        "query": "What is the bereavement leave policy?",
        "role": "hr",
        "expected_route": "hr",
        "expected_access": True,
        "expected_sources": ["leave_policies.txt"],
        "answer_keywords": ["bereavement", "5 paid"],
    },
    # Finance
    {
        "id": "FIN-01",
        "category": "Finance",
        "query": "What was Engineering's Q2 budget?",
        "role": "finance",
        "expected_route": "finance",
        "expected_access": True,
        "expected_sources": ["department_budgets.txt", "finance_report.txt"],
        "answer_keywords": ["3,200,000", "Engineering"],
    },
    {
        "id": "FIN-02",
        "category": "Finance",
        "query": "What was company revenue in Q3?",
        "role": "finance",
        "expected_route": "finance",
        "expected_access": True,
        "expected_sources": ["quarterly_reports.txt", "revenue_reports.txt", "finance_report.txt"],
        "answer_keywords": ["revenue", "q3"],
    },
    {
        "id": "FIN-03",
        "category": "Finance",
        "query": "Which department had the highest expenses?",
        "role": "finance",
        "expected_route": "finance",
        "expected_access": True,
        "expected_sources": ["expense_reports.txt", "finance_report.txt"],
        "answer_keywords": ["Sales", "4,500,000"],
    },
    {
        "id": "FIN-04",
        "category": "Finance",
        "query": "What was Sales revenue in Q3?",
        "role": "finance",
        "expected_route": "finance",
        "expected_access": True,
        "expected_sources": ["revenue_reports.txt", "quarterly_reports.txt"],
        "answer_keywords": ["7,500,000", "sales"],
    },
    {
        "id": "FIN-05",
        "category": "Finance",
        "query": "What is the approved annual budget for 2025?",
        "role": "finance",
        "expected_route": "finance",
        "expected_access": True,
        "expected_sources": ["department_budgets.txt", "finance_report.txt"],
        "answer_keywords": ["40,000,000", "budget"],
    },
    {
        "id": "FIN-06",
        "category": "Finance",
        "query": "What was Engineering revenue in Q3?",
        "role": "finance",
        "expected_route": "finance",
        "expected_access": True,
        "expected_sources": ["revenue_reports.txt", "quarterly_reports.txt"],
        "answer_keywords": ["4,800,000", "Engineering"],
    },
    # Security
    {
        "id": "SEC-01",
        "category": "Security",
        "query": "Is MFA required?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["mfa_policy.txt", "it_security_policy.pdf"],
        "answer_keywords": ["MFA", "mandatory"],
    },
    {
        "id": "SEC-02",
        "category": "Security",
        "query": "What are the password requirements?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["password_policy.txt", "it_security_policy.pdf"],
        "answer_keywords": ["14 characters", "90 days"],
    },
    {
        "id": "SEC-03",
        "category": "Security",
        "query": "Were there malware incidents in June?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["security_logs.json"],
        "answer_keywords": ["malware", "Trojan"],
    },
    {
        "id": "SEC-04",
        "category": "Security",
        "query": "How many failed logins occurred?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["security_logs.json"],
        "answer_keywords": ["failed login", "login"],
    },
    {
        "id": "SEC-05",
        "category": "Security",
        "query": "How soon must security incidents be reported?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["incident_response.txt"],
        "answer_keywords": ["incident", "15 minutes"],
    },
    {
        "id": "SEC-06",
        "category": "Security",
        "query": "What happens after 5 failed login attempts?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["password_policy.txt", "security_logs.json"],
        "answer_keywords": ["locked", "30 minutes"],
    },
    {
        "id": "SEC-07",
        "category": "Security",
        "query": "Were there UNAUTHORIZED_ACCESS events in the security logs?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["security_logs.json"],
        "answer_keywords": ["security events", "june"],
    },
    {
        "id": "SEC-08",
        "category": "Security",
        "query": "What are the enterprise security policy principles?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["security_policy.txt"],
        "answer_keywords": ["enterprise security policy principles"],
    },
    # Cross-source
    {
        "id": "XSR-01",
        "category": "Cross-source",
        "query": "Which employee was affected by a security incident?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["security_logs.json", "employees.csv"],
        "answer_keywords": ["incident", "affected"],
    },
    {
        "id": "XSR-02",
        "category": "Cross-source",
        "query": "Which department generated the highest revenue and who manages it?",
        "role": "admin",
        "expected_route": "finance",
        "expected_access": True,
        "expected_sources": ["quarterly_reports.txt", "revenue_reports.txt", "employees.csv"],
        "answer_keywords": ["emily davis", "sales"],
    },
    {
        "id": "XSR-03",
        "category": "Cross-source",
        "query": "Are remote workers required to use MFA?",
        "role": "admin",
        "expected_route": "hr",
        "expected_access": True,
        "expected_sources": ["remote_work_policy.txt", "mfa_policy.txt"],
        "answer_keywords": ["mfa", "remote"],
    },
    {
        "id": "XSR-04",
        "category": "Cross-source",
        "query": "What is Michael Chen's salary?",
        "role": "hr",
        "expected_route": "employee",
        "expected_access": True,
        "expected_sources": ["employees.csv"],
        "answer_keywords": ["michael chen", "98,000"],
    },
    {
        "id": "XSR-05",
        "category": "Cross-source",
        "query": "Who is the manager of the Sales department?",
        "role": "admin",
        "expected_route": "hr",
        "expected_access": True,
        "expected_sources": ["employees.csv", "quarterly_reports.txt"],
        "answer_keywords": ["emily davis", "sales"],
    },
    {
        "id": "XSR-06",
        "category": "Cross-source",
        "query": "What privilege escalation incident involved Michael Chen?",
        "role": "admin",
        "expected_route": "security",
        "expected_access": True,
        "expected_sources": ["security_logs.json", "employees.csv"],
        "answer_keywords": ["privilege escalation"],
    },
    # RBAC
    {
        "id": "RBAC-01",
        "category": "RBAC",
        "query": "Show me all employee salary records",
        "role": "employee",
        "expected_route": "employee",
        "expected_access": False,
        "expected_sources": [],
        "answer_keywords": [],
    },
    {
        "id": "RBAC-02",
        "category": "RBAC",
        "query": "Were there malware incidents in June?",
        "role": "finance",
        "expected_route": "security",
        "expected_access": False,
        "expected_sources": [],
        "answer_keywords": [],
    },
    {
        "id": "RBAC-03",
        "category": "RBAC",
        "query": "What was company revenue in Q3?",
        "role": "hr",
        "expected_route": "finance",
        "expected_access": False,
        "expected_sources": [],
        "answer_keywords": [],
    },
    {
        "id": "RBAC-04",
        "category": "RBAC",
        "query": "What are the password requirements?",
        "role": "employee",
        "expected_route": "security",
        "expected_access": False,
        "expected_sources": [],
        "answer_keywords": [],
    },
]


@dataclass
class CaseResult:
    test_id: str
    category: str
    query: str
    role: str
    passed: bool
    expected_route: str
    actual_route: str
    expected_access: bool
    actual_access: bool
    expected_sources: list[str]
    actual_sources: list[str]
    confidence: float
    answer: str
    checks: dict
    message: str


@dataclass
class EnterpriseTestReport:
    timestamp: str
    dataset_count: int
    chunk_count: int
    total: int = 0
    passed: int = 0
    failed: int = 0
    by_category: dict = field(default_factory=dict)
    results: list[CaseResult] = field(default_factory=list)

    def add(self, result: CaseResult) -> None:
        self.results.append(result)
        self.total += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
        self.by_category.setdefault(result.category, {"passed": 0, "failed": 0})
        key = "passed" if result.passed else "failed"
        self.by_category[result.category][key] += 1


def evaluate_case(case: dict, rag: EnterpriseRAG) -> CaseResult:
    response = rag.query(case["query"], case["role"])
    answer_lower = response.answer.lower()

    route_ok = response.routed_category == case["expected_route"]
    access_ok = response.access_granted == case["expected_access"]

    if case["expected_sources"]:
        sources_ok = any(src in response.sources_used for src in case["expected_sources"])
    else:
        sources_ok = len(response.sources_used) == 0

    keywords_ok = (
        all(kw.lower() in answer_lower for kw in case["answer_keywords"])
        if case["expected_access"] and case["answer_keywords"]
        else True
    )

    passed = route_ok and access_ok and sources_ok and keywords_ok

    checks = {
        "route_ok": route_ok,
        "access_ok": access_ok,
        "sources_ok": sources_ok,
        "keywords_ok": keywords_ok,
    }

    failures = [name for name, ok in checks.items() if not ok]
    message = "All checks passed" if passed else f"Failed: {', '.join(failures)}"

    return CaseResult(
        test_id=case["id"],
        category=case["category"],
        query=case["query"],
        role=case["role"],
        passed=passed,
        expected_route=case["expected_route"],
        actual_route=response.routed_category,
        expected_access=case["expected_access"],
        actual_access=response.access_granted,
        expected_sources=case["expected_sources"],
        actual_sources=response.sources_used,
        confidence=response.confidence_score,
        answer=response.answer,
        checks=checks,
        message=message,
    )


def save_outputs(report: EnterpriseTestReport) -> None:
    payload = {
        "timestamp": report.timestamp,
        "summary": {
            "dataset_count": report.dataset_count,
            "chunk_count": report.chunk_count,
            "total": report.total,
            "passed": report.passed,
            "failed": report.failed,
            "pass_rate": round(report.passed / report.total * 100, 1) if report.total else 0,
            "by_category": report.by_category,
        },
        "results": [asdict(r) for r in report.results],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "ACME Enterprise RAG — Realistic Test Results",
        f"Run at: {report.timestamp}",
        f"Datasets: {report.dataset_count} files | Chunks indexed: {report.chunk_count}",
        "",
        f"SUMMARY: {report.passed}/{report.total} passed ({payload['summary']['pass_rate']}%)",
        "",
    ]

    for category, counts in sorted(report.by_category.items()):
        lines.append(f"  {category}: {counts['passed']} passed, {counts['failed']} failed")

    lines.append("")
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.test_id} ({result.category})")
        lines.append(f"       Q: {result.query}")
        lines.append(f"       Role: {result.role} | Route: {result.actual_route} | Access: {result.actual_access}")
        lines.append(f"       Sources: {result.actual_sources}")
        lines.append(f"       {result.message}")
        lines.append("")

    RESULTS_TXT.write_text("\n".join(lines), encoding="utf-8")

    md = [
        "# ACME Enterprise RAG — Realistic Test Report",
        "",
        f"**Run date:** {report.timestamp}",
        f"**Datasets loaded:** {report.dataset_count} files",
        f"**Chunks indexed:** {report.chunk_count}",
        f"**Result:** {report.passed}/{report.total} passed ({payload['summary']['pass_rate']}%)",
        "",
        "## Summary by Category",
        "",
        "| Category | Passed | Failed |",
        "|----------|--------|--------|",
    ]

    for category, counts in sorted(report.by_category.items()):
        md.append(f"| {category} | {counts['passed']} | {counts['failed']} |")

    md.extend([
        "",
        "## Enterprise Datasets",
        "",
        "The test corpus simulates a real company knowledge base:",
        "",
        "### HR Documents",
        "- `employee_handbook.txt` — code of conduct and workplace standards",
        "- `leave_policies.txt` — annual, sick, maternity, bereavement leave",
        "- `remote_work_policy.txt` — hybrid work and MFA requirements for remote staff",
        "- `performance_review_policy.txt` — review frequency and rating scale",
        "",
        "### Finance Documents",
        "- `quarterly_reports.txt` — Q2/Q3 company and department summaries",
        "- `department_budgets.txt` — Engineering Q2 budget and annual budgets",
        "- `revenue_reports.txt` — department revenue by quarter",
        "- `expense_reports.txt` — department expenses and highest-spend analysis",
        "",
        "### Security Documents",
        "- `security_policy.txt` — enterprise security principles",
        "- `mfa_policy.txt` — MFA enrollment requirements",
        "- `password_policy.txt` — password and lockout rules",
        "- `incident_response.txt` — reporting and response procedures",
        "- `security_logs.json` — June 2025 SIEM events",
        "- `it_security_policy.pdf` — IT security policy (PDF)",
        "",
        "### Employee Records",
        "- `employees.csv` — 15 employees with salaries, managers, security incidents",
        "",
        "## Test Results",
        "",
        "| ID | Category | Query | Role | Route | Access | Sources | Status |",
        "|----|----------|-------|------|-------|--------|---------|--------|",
    ])

    for r in report.results:
        status = "PASS" if r.passed else "FAIL"
        sources = ", ".join(r.actual_sources) if r.actual_sources else "—"
        md.append(
            f"| {r.test_id} | {r.category} | {r.query[:40]} | {r.role} "
            f"| {r.actual_route} | {r.actual_access} | {sources} | {status} |"
        )

    md.extend([
        "",
        "## Failed Tests",
        "",
    ])

    failed = [r for r in report.results if not r.passed]
    if failed:
        for r in failed:
            md.append(f"### {r.test_id}: {r.query}")
            md.append(f"- Expected route: `{r.expected_route}` → Actual: `{r.actual_route}`")
            md.append(f"- Expected access: `{r.expected_access}` → Actual: `{r.actual_access}`")
            md.append(f"- Expected sources: `{r.expected_sources}`")
            md.append(f"- Actual sources: `{r.actual_sources}`")
            md.append(f"- Answer: {r.answer[:200]}")
            md.append(f"- Failed checks: {r.message}")
            md.append("")
    else:
        md.append("All tests passed.")
        md.append("")

    md.extend([
        "## How to Reproduce",
        "",
        "```bash",
        "python realistic_enterprise_test.py",
        "```",
        "",
        "Output files:",
        "- `results/realistic_test_results.json`",
        "- `results/realistic_test_results.txt`",
        "- `results/realistic_test_report.md`",
    ])

    REPORT_MD.write_text("\n".join(md), encoding="utf-8")


def main() -> int:
    print("ACME Enterprise RAG — Realistic Test Suite")
    print("=" * 55)

    sources_on_disk = sorted(p.name for p in DATA_DIR.iterdir() if p.is_file())
    chunks = load_documents(DATA_DIR)

    print(f"Datasets on disk: {len(sources_on_disk)}")
    print(f"Chunks loaded:    {len(chunks)}")
    print("Initializing RAG pipeline (loading embedding model)...")

    report = EnterpriseTestReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        dataset_count=len(sources_on_disk),
        chunk_count=len(chunks),
    )

    try:
        rag = EnterpriseRAG()
        rag.initialize()

        for case in TEST_CASES:
            result = evaluate_case(case, rag)
            report.add(result)
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {result.test_id}: {result.message}")

    except Exception as exc:
        print(f"FATAL: {exc}")
        traceback.print_exc()
        return 1

    save_outputs(report)

    print("\n" + "=" * 55)
    print(f"SUMMARY: {report.passed}/{report.total} passed, {report.failed} failed")
    print(f"Results: {RESULTS_JSON}")
    print(f"         {RESULTS_TXT}")
    print(f"         {REPORT_MD}")

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
