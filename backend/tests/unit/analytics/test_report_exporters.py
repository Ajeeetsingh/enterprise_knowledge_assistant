"""Unit tests for analytics exporters (Phase 11.7)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.analytics.exporters.csv_exporter import CSVReportExporter
from app.analytics.exporters.excel_exporter import ExcelReportExporter
from app.analytics.exporters.pdf_exporter import PDFReportExporter
from app.analytics.services.report_payload import AnalyticsReportPayload, ReportTableSection, ReportTrendSection


def _sample_payload() -> AnalyticsReportPayload:
    return AnalyticsReportPayload(
        module="user",
        module_title="User Analytics",
        generated_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        start_date=datetime(2026, 6, 1, tzinfo=UTC),
        end_date=datetime(2026, 6, 24, tzinfo=UTC),
        kpis=(("Total Users", "10"), ("New Users", "2")),
        tables=(
            ReportTableSection(
                name="Top Active Users",
                headers=("Email", "Questions"),
                rows=(("admin@example.com", "5"),),
            ),
        ),
        trends=(
            ReportTrendSection(
                name="Questions Asked",
                points={"2026-06-01": 3, "2026-06-02": 5},
            ),
        ),
    )


class TestReportExporters:
    def test_csv_exporter_returns_utf8_bytes(self) -> None:
        content = CSVReportExporter().export(_sample_payload())

        assert isinstance(content, bytes)
        text = content.decode("utf-8")
        assert "User Analytics" in text
        assert "KPI Summary" in text
        assert "Top Active Users" in text

    def test_excel_exporter_returns_xlsx_signature(self) -> None:
        content = ExcelReportExporter().export(_sample_payload())

        assert content.startswith(b"PK")

    def test_pdf_exporter_returns_pdf_signature(self) -> None:
        content = PDFReportExporter().export(_sample_payload())

        assert content.startswith(b"%PDF")
