"""Unit tests for analytics report repository (Phase 11.7)."""

from __future__ import annotations

import pytest

from app.analytics.repositories.report_repository import (
    ReportFormat,
    ReportModule,
    ReportRepository,
)


class TestReportRepository:
    def test_list_modules_includes_all_analytics_domains(self) -> None:
        repository = ReportRepository()
        module_ids = {module.id for module in repository.list_modules()}

        assert module_ids == {
            ReportModule.USER,
            ReportModule.AI,
            ReportModule.KNOWLEDGE,
            ReportModule.MONITORING,
            ReportModule.ERRORS,
        }

    def test_list_formats_includes_csv_xlsx_pdf(self) -> None:
        repository = ReportRepository()
        format_ids = {report_format.id for report_format in repository.list_formats()}

        assert format_ids == {ReportFormat.CSV, ReportFormat.XLSX, ReportFormat.PDF}

    def test_get_module_raises_for_unknown_module(self) -> None:
        repository = ReportRepository()

        with pytest.raises(KeyError):
            repository.get_module("unknown")  # type: ignore[arg-type]
