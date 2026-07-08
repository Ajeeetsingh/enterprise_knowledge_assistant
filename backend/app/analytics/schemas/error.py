"""Pydantic models for error analytics APIs (Phase 11.6)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.schemas.common import ChartSeries

if TYPE_CHECKING:
    from app.analytics.services.error_analytics_service import (
        EndpointFailureSnapshot,
        ErrorCategorySnapshot,
        ErrorOverviewSnapshot,
        ErrorTrendsSnapshot,
        FailureAnalysisSnapshot,
    )


class ErrorOverviewResponse(BaseModel):
    """Administrator KPI summary for operational failures."""

    model_config = ConfigDict(from_attributes=True)

    total_errors: int = Field(ge=0)
    authentication_failures: int = Field(ge=0)
    authorization_failures: int = Field(ge=0)
    upload_failures: int | None = Field(default=None, ge=0)
    indexing_failures: int | None = Field(default=None, ge=0)
    retrieval_failures: int = Field(ge=0)
    api_errors: int | None = Field(
        default=None,
        ge=0,
        description="Not instrumented; returns null until API exception audit events exist.",
    )
    background_job_failures: int | None = Field(
        default=None,
        ge=0,
        description="Not instrumented; returns null until background worker audit events exist.",
    )
    error_rate: float = Field(ge=0.0, le=100.0)
    error_free_requests_percentage: float = Field(ge=0.0, le=100.0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: ErrorOverviewSnapshot) -> ErrorOverviewResponse:
        """Build an API response from a service-layer overview."""
        return cls.model_validate(snapshot)


class ErrorTrendsResponse(BaseModel):
    """Time-series data for operational failures."""

    model_config = ConfigDict(from_attributes=True)

    total_errors: ChartSeries
    authentication_failures: ChartSeries
    retrieval_failures: ChartSeries
    upload_failures: ChartSeries
    api_exceptions: ChartSeries
    permission_denials: ChartSeries
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: ErrorTrendsSnapshot) -> ErrorTrendsResponse:
        """Build an API response from a service-layer trends snapshot."""
        return cls.model_validate(snapshot)


class ErrorFrequencyItemResponse(BaseModel):
    """Single row in recurring error analytics."""

    label: str
    count: int = Field(ge=1)
    category: str


class ErrorCategoryResponse(BaseModel):
    """Error breakdown by category and recurring patterns."""

    model_config = ConfigDict(from_attributes=True)

    by_category: dict[str, int] = Field(default_factory=dict)
    by_service: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] | None = Field(
        default=None,
        description="Not instrumented; returns null until severity metadata is persisted.",
    )
    recurring_errors: list[ErrorFrequencyItemResponse]
    total_recurring_errors: int = Field(ge=0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: ErrorCategorySnapshot) -> ErrorCategoryResponse:
        """Build an API response from a service-layer category snapshot."""
        return cls(
            by_category=snapshot.by_category,
            by_service=snapshot.by_service,
            by_severity=snapshot.by_severity,
            recurring_errors=[
                ErrorFrequencyItemResponse(
                    label=str(item["label"]),
                    count=int(item["count"]),
                    category=str(item["category"]),
                )
                for item in snapshot.recurring_errors
            ],
            total_recurring_errors=snapshot.total_recurring_errors,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )


class EndpointFailureItemResponse(BaseModel):
    """Single row in endpoint failure analytics."""

    endpoint: str
    count: int = Field(ge=1)
    service: str


class EndpointFailureResponse(BaseModel):
    """Endpoint failure analytics summary."""

    model_config = ConfigDict(from_attributes=True)

    items: list[EndpointFailureItemResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: EndpointFailureSnapshot) -> EndpointFailureResponse:
        """Build an API response from a service-layer endpoint snapshot."""
        return cls(
            items=[
                EndpointFailureItemResponse(
                    endpoint=str(item["endpoint"]),
                    count=int(item["count"]),
                    service=str(item["service"]),
                )
                for item in snapshot.items
            ],
            total=snapshot.total,
            limit=snapshot.limit,
            offset=snapshot.offset,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )


class FailureAnalysisResponse(BaseModel):
    """Failure analysis across operations and services."""

    model_config = ConfigDict(from_attributes=True)

    failed_operations: list[ErrorFrequencyItemResponse]
    retrieval_failures: list[ErrorFrequencyItemResponse]
    upload_failures: list[ErrorFrequencyItemResponse]
    authentication_failures: list[ErrorFrequencyItemResponse]
    total_failed_operations: int = Field(ge=0)
    total_retrieval_failures: int = Field(ge=0)
    total_upload_failures: int = Field(ge=0)
    total_authentication_failures: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: FailureAnalysisSnapshot) -> FailureAnalysisResponse:
        """Build an API response from a service-layer failure snapshot."""

        def _items(rows: list[dict[str, object]]) -> list[ErrorFrequencyItemResponse]:
            return [
                ErrorFrequencyItemResponse(
                    label=str(item["label"]),
                    count=int(item["count"]),
                    category=str(item["category"]),
                )
                for item in rows
            ]

        return cls(
            failed_operations=_items(snapshot.failed_operations),
            retrieval_failures=_items(snapshot.retrieval_failures),
            upload_failures=_items(snapshot.upload_failures),
            authentication_failures=_items(snapshot.authentication_failures),
            total_failed_operations=snapshot.total_failed_operations,
            total_retrieval_failures=snapshot.total_retrieval_failures,
            total_upload_failures=snapshot.total_upload_failures,
            total_authentication_failures=snapshot.total_authentication_failures,
            limit=snapshot.limit,
            offset=snapshot.offset,
            start_date=snapshot.start_date,
            end_date=snapshot.end_date,
        )
