"""Analytics API filter and grouping schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GroupBy(StrEnum):
    """Supported time buckets for aggregated analytics series."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class DateRangePreset(StrEnum):
    """Predefined reporting windows for analytics dashboards."""

    TODAY = "today"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    CUSTOM = "custom"


class DateRange(BaseModel):
    """Inclusive UTC reporting window supplied by API clients."""

    model_config = ConfigDict(extra="forbid")

    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def validate_range(self) -> DateRange:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date.")
        return self


class AnalyticsFilter(BaseModel):
    """Optional analytics query parameters for dashboard and report APIs."""

    model_config = ConfigDict(extra="forbid")

    range_preset: DateRangePreset | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    group_by: GroupBy | None = None
    limit: int | None = Field(default=None, ge=1, le=365)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> AnalyticsFilter:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must be before or equal to end_date.")
        return self
