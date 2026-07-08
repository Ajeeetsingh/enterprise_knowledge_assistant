"""Report module and format metadata for analytics exports (Phase 11.7)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReportModule(StrEnum):
    """Supported analytics modules for export."""

    USER = "user"
    AI = "ai"
    KNOWLEDGE = "knowledge"
    MONITORING = "monitoring"
    ERRORS = "errors"


class ReportFormat(StrEnum):
    """Supported export file formats."""

    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


@dataclass(frozen=True)
class ReportModuleDefinition:
    """Metadata describing an exportable analytics module."""

    id: ReportModule
    title: str
    description: str


@dataclass(frozen=True)
class ReportFormatDefinition:
    """Metadata describing an export format."""

    id: ReportFormat
    label: str
    media_type: str
    extension: str


class ReportRepository:
    """Static catalog of export modules and formats."""

    _MODULES: tuple[ReportModuleDefinition, ...] = (
        ReportModuleDefinition(
            id=ReportModule.USER,
            title="User Analytics",
            description="User adoption, engagement, and activity metrics.",
        ),
        ReportModuleDefinition(
            id=ReportModule.AI,
            title="AI Analytics",
            description="AI performance, retrieval quality, and assistant effectiveness.",
        ),
        ReportModuleDefinition(
            id=ReportModule.KNOWLEDGE,
            title="Knowledge Analytics",
            description="Knowledge base health, usage, and content freshness.",
        ),
        ReportModuleDefinition(
            id=ReportModule.MONITORING,
            title="System Monitoring",
            description="Operational health, performance, and resource metrics.",
        ),
        ReportModuleDefinition(
            id=ReportModule.ERRORS,
            title="Error Analytics",
            description="Operational failures and recurring error patterns.",
        ),
    )

    _FORMATS: tuple[ReportFormatDefinition, ...] = (
        ReportFormatDefinition(
            id=ReportFormat.CSV,
            label="CSV",
            media_type="text/csv",
            extension="csv",
        ),
        ReportFormatDefinition(
            id=ReportFormat.XLSX,
            label="Excel (.xlsx)",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            extension="xlsx",
        ),
        ReportFormatDefinition(
            id=ReportFormat.PDF,
            label="PDF",
            media_type="application/pdf",
            extension="pdf",
        ),
    )

    def list_modules(self) -> list[ReportModuleDefinition]:
        """Return exportable analytics modules."""
        return list(self._MODULES)

    def list_formats(self) -> list[ReportFormatDefinition]:
        """Return supported export formats."""
        return list(self._FORMATS)

    def get_module(self, module: ReportModule) -> ReportModuleDefinition:
        """Return module metadata or raise ``KeyError``."""
        for definition in self._MODULES:
            if definition.id == module:
                return definition
        raise KeyError(module)

    def get_format(self, report_format: ReportFormat) -> ReportFormatDefinition:
        """Return format metadata or raise ``KeyError``."""
        for definition in self._FORMATS:
            if definition.id == report_format:
                return definition
        raise KeyError(report_format)
