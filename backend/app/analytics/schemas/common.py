"""Shared analytics metric and chart schema models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MetricSummary(BaseModel):
    """Numeric KPI summary for a reporting window."""

    model_config = ConfigDict(from_attributes=True)

    questions_asked: int = Field(ge=0)
    answers_generated: int = Field(ge=0)
    retrieval_failures: int = Field(ge=0)
    average_confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    average_citation_count: float | None = Field(default=None, ge=0.0)

    @classmethod
    def from_snapshot(cls, snapshot: object) -> MetricSummary:
        """Build a metric summary from a repository chat snapshot."""
        return cls.model_validate(snapshot)


class TimeSeries(BaseModel):
    """Generic time-indexed metric values."""

    label: str
    points: dict[str, float | int] = Field(
        description="Bucket key (e.g. UTC date) to metric value.",
    )


class ChartSeries(BaseModel):
    """Daily event counts for a single audit event type."""

    event_type: str
    points: dict[str, int] = Field(
        description="UTC date (YYYY-MM-DD) to event count.",
    )
