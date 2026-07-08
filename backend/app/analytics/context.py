"""Shared analytics query context for repositories and services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

GroupByValue = Literal["day", "week", "month"]


@dataclass(frozen=True)
class AnalyticsContext:
    """Reusable filter window and presentation options for analytics queries."""

    start_date: datetime
    end_date: datetime
    timezone: str = "UTC"
    group_by: GroupByValue | None = None
    limit: int | None = None

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date.")
