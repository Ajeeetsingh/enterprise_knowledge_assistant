"""Reporting and export schemas for analytics (Phase 11.7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analytics.repositories.report_repository import ReportFormat, ReportModule
from app.analytics.schemas.filters import DateRangePreset


class ReportExportRequest(BaseModel):
    """Request body for analytics report export."""

    model_config = ConfigDict(extra="forbid")

    module: ReportModule
    format: ReportFormat
    date_range: DateRangePreset | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None

    @model_validator(mode="after")
    def validate_range(self) -> ReportExportRequest:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must be before or equal to end_date.")
        return self


class ReportModuleResponse(BaseModel):
    """Exportable analytics module metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str


class ReportFormatResponse(BaseModel):
    """Supported export format metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    label: str
    media_type: str
    extension: str


class ReportModulesResponse(BaseModel):
    """Catalog of exportable analytics modules."""

    items: list[ReportModuleResponse]


class ReportFormatsResponse(BaseModel):
    """Catalog of supported export formats."""

    items: list[ReportFormatResponse]


class ReportExportMetadata(BaseModel):
    """Non-file metadata returned when clients request JSON export details."""

    filename: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    module: ReportModule
    format: ReportFormat
    start_date: datetime
    end_date: datetime
