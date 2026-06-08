"""End-to-end test suite for the Enterprise RAG pipeline.

Usage:
    python test_pipeline.py
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
from app.rag.rbac import can_access, get_accessible_categories
from app.rag.router import route_query

REPO_ROOT = BACKEND_ROOT.parent
DATA_DIR = BACKEND_ROOT / "tests" / "fixtures" / "sample_docs"
RESULTS_DIR = REPO_ROOT / "results"
RESULTS_JSON = RESULTS_DIR / "test_results.json"
RESULTS_TXT = RESULTS_DIR / "test_results.txt"

EXPECTED_SOURCES = {
    "hr_policy.txt",
    "finance_report.txt",
    "security_logs.json",
    "employees.csv",
    "it_security_policy.pdf",
}


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class TestReport:
    timestamp: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: list[TestResult] = field(default_factory=list)

    def add(self, result: TestResult) -> None:
        self.results.append(result)
        self.total += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
            },
            "results": [asdict(r) for r in self.results],
        }


def record(report: TestReport, name: str, passed: bool, message: str, **details) -> None:
    report.add(TestResult(name=name, passed=passed, message=message, details=details))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}: {message}")


def test_ingestion(report: TestReport) -> list:
    print("\n--- Ingestion ---")
    try:
        chunks = load_documents(DATA_DIR)
        sources = {c.source for c in chunks}
        categories = {c.source: c.category for c in chunks}
        pdf_chunks = [c for c in chunks if c.source.endswith(".pdf")]

        record(
            report,
            "ingestion_loads_all_files",
            EXPECTED_SOURCES.issubset(sources),
            f"Loaded {len(sources)} sources, {len(chunks)} chunks",
            sources=sorted(sources),
            chunk_count=len(chunks),
        )

        record(
            report,
            "ingestion_pdf_supported",
            len(pdf_chunks) > 0 and "it_security_policy.pdf" in sources,
            f"PDF chunks: {len(pdf_chunks)}",
            pdf_chunk_count=len(pdf_chunks),
            pdf_sample=pdf_chunks[0].content[:120] if pdf_chunks else "",
        )

        record(
            report,
            "ingestion_category_mapping",
            categories.get("it_security_policy.pdf") == "security"
            and categories.get("hr_policy.txt") == "hr",
            "Category map correct for PDF and HR",
            categories=categories,
        )

        return chunks
    except Exception as exc:
        record(report, "ingestion_error", False, str(exc), traceback=traceback.format_exc())
        return []


def test_router(report: TestReport) -> None:
    print("\n--- Router ---")
    cases = [
        ("What is the parental leave policy?", "hr"),
        ("What was Q3 revenue for Sales?", "finance"),
        ("Were there any malware incidents?", "security"),
        ("What is Jane Smith salary?", "employee"),
        ("What are the password requirements?", "security"),
        ("What is the password policy?", "security"),
        ("Is MFA mandatory?", "security"),
        ("What is the multi factor authentication policy?", "security"),
        ("What are the failed login attempts?", "security"),
        ("What is the access control policy?", "security"),
    ]
    for query, expected_category in cases:
        route = route_query(query)
        record(
            report,
            f"router_{expected_category}",
            route.category == expected_category,
            f"'{query[:40]}...' -> {route.category} (confidence {route.confidence})",
            query=query,
            expected=expected_category,
            actual=route.category,
            confidence=route.confidence,
            keywords=route.matched_keywords,
        )


def test_rbac(report: TestReport) -> None:
    print("\n--- RBAC ---")
    allow_cases = [
        ("admin", "security", True),
        ("hr", "employee", True),
        ("finance", "finance", True),
        ("employee", "hr", True),
    ]
    deny_cases = [
        ("employee", "employee", False),
        ("employee", "security", False),
        ("finance", "security", False),
        ("hr", "finance", False),
    ]

    for role, category, expected in allow_cases + deny_cases:
        actual = can_access(role, category)
        record(
            report,
            f"rbac_{role}_{category}",
            actual == expected,
            f"{role} -> {category}: {'allowed' if actual else 'denied'}",
            role=role,
            category=category,
            expected=expected,
            actual=actual,
        )

    for role in ("admin", "hr", "finance", "employee"):
        categories = get_accessible_categories(role)
        record(
            report,
            f"rbac_categories_{role}",
            len(categories) > 0,
            f"{role} can access: {categories}",
            role=role,
            categories=categories,
        )


def test_end_to_end(report: TestReport, rag: EnterpriseRAG) -> None:
    print("\n--- End-to-End Queries ---")
    cases = [
        {
            "name": "hr_parental_leave",
            "query": "What is the parental leave policy?",
            "role": "hr",
            "expect_access": True,
            "answer_contains": ["primary caregivers", "16 weeks"],
            "sources_contain": ["hr_policy.txt"],
        },
        {
            "name": "employee_remote_work",
            "query": "What is the remote work policy?",
            "role": "employee",
            "expect_access": True,
            "answer_contains": ["remote", "3 days"],
            "sources_contain": ["hr_policy.txt"],
        },
        {
            "name": "finance_sales_revenue",
            "query": "What was Q3 revenue for the Sales department?",
            "role": "finance",
            "expect_access": True,
            "answer_contains": ["7,500,000"],
            "sources_contain": ["finance_report.txt"],
        },
        {
            "name": "admin_malware",
            "query": "Were there any malware incidents?",
            "role": "admin",
            "expect_access": True,
            "answer_contains": ["malware", "Trojan"],
            "sources_contain": ["security_logs.json"],
        },
        {
            "name": "admin_pdf_password",
            "query": "What are the password requirements?",
            "role": "admin",
            "expect_access": True,
            "answer_contains": ["14 characters", "90 days"],
            "sources_contain": ["it_security_policy.pdf"],
        },
        {
            "name": "admin_pdf_mfa",
            "query": "Is MFA mandatory?",
            "role": "admin",
            "expect_access": True,
            "answer_contains": ["MFA", "mandatory"],
            "sources_contain": ["it_security_policy.pdf"],
        },
        {
            "name": "hr_employee_salary",
            "query": "What is Jane Smith salary?",
            "role": "hr",
            "expect_access": True,
            "answer_contains": ["Jane Smith", "145,000"],
            "sources_contain": ["employees.csv"],
        },
        {
            "name": "employee_salary_denied",
            "query": "Show me employee salary records",
            "role": "employee",
            "expect_access": False,
            "answer_contains": [],
            "sources_contain": [],
        },
        {
            "name": "finance_security_denied",
            "query": "What were the failed login attempts?",
            "role": "finance",
            "expect_access": False,
            "answer_contains": [],
            "sources_contain": [],
        },
        {
            "name": "employee_security_denied",
            "query": "Were there any malware incidents?",
            "role": "employee",
            "expect_access": False,
            "answer_contains": [],
            "sources_contain": [],
        },
        {
            "name": "employee_password_denied",
            "query": "What are the password requirements?",
            "role": "employee",
            "expect_access": False,
            "answer_contains": [],
            "sources_contain": [],
        },
    ]

    for case in cases:
        response = rag.query(case["query"], case["role"])
        answer_lower = response.answer.lower()

        access_ok = response.access_granted == case["expect_access"]
        answer_ok = all(term.lower() in answer_lower for term in case["answer_contains"])
        sources_ok = all(src in response.sources_used for src in case["sources_contain"])
        confidence_ok = (
            response.confidence_score > 0 if case["expect_access"] and case["answer_contains"]
            else True
        )
        citations_ok = len(response.citations) > 0 if case["expect_access"] and case["sources_contain"] else True

        passed = access_ok and answer_ok and sources_ok and confidence_ok and citations_ok

        record(
            report,
            f"e2e_{case['name']}",
            passed,
            f"access={response.access_granted}, sources={response.sources_used}, "
            f"confidence={response.confidence_score}",
            query=case["query"],
            role=case["role"],
            routed_category=response.routed_category,
            access_granted=response.access_granted,
            expected_access=case["expect_access"],
            answer=response.answer,
            sources_used=response.sources_used,
            citations=[asdict(c) for c in response.citations],
            confidence_score=response.confidence_score,
            checks={
                "access_ok": access_ok,
                "answer_ok": answer_ok,
                "sources_ok": sources_ok,
                "confidence_ok": confidence_ok,
                "citations_ok": citations_ok,
            },
        )


def save_results(report: TestReport) -> None:
    report_dict = report.to_dict()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")

    lines = [
        "Enterprise RAG Pipeline - Test Results",
        f"Run at: {report.timestamp}",
        "",
        f"Summary: {report.passed}/{report.total} passed, {report.failed} failed",
        "",
    ]

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"[{status}] {result.name}")
        lines.append(f"       {result.message}")
        if not result.passed and result.details:
            lines.append(f"       Details: {json.dumps(result.details, default=str)[:200]}")
        lines.append("")

    RESULTS_TXT.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nResults saved to:")
    print(f"  {RESULTS_JSON}")
    print(f"  {RESULTS_TXT}")


def main() -> int:
    print("Enterprise RAG Pipeline - Test Suite")
    print("=" * 50)

    report = TestReport(timestamp=datetime.now(timezone.utc).isoformat())

    chunks = test_ingestion(report)
    test_router(report)
    test_rbac(report)

    if chunks:
        print("\n--- Initializing RAG (loads embedding model) ---")
        try:
            rag = EnterpriseRAG()
            chunk_count = rag.initialize()
            record(
                report,
                "rag_initialize",
                chunk_count >= len(EXPECTED_SOURCES),
                f"Indexed {chunk_count} chunks",
                chunk_count=chunk_count,
            )
            test_end_to_end(report, rag)
        except Exception as exc:
            record(
                report,
                "rag_initialize_error",
                False,
                str(exc),
                traceback=traceback.format_exc(),
            )
    else:
        record(report, "rag_skipped", False, "Skipped RAG tests due to ingestion failure")

    save_results(report)

    print("\n" + "=" * 50)
    print(f"SUMMARY: {report.passed}/{report.total} passed, {report.failed} failed")

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
