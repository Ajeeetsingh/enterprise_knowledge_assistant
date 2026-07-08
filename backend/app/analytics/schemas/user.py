"""Pydantic models for user analytics APIs (Phase 11.2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.schemas.common import ChartSeries

if TYPE_CHECKING:
    from app.analytics.services.user_analytics_service import (
        UserActivitySnapshot,
        UserAnalyticsOverviewSnapshot,
        UserGrowthTrendsSnapshot,
    )


class UserAnalyticsOverviewResponse(BaseModel):
    """Administrator KPI summary for user adoption and engagement."""

    model_config = ConfigDict(from_attributes=True)

    total_users: int = Field(ge=0)
    new_users: int = Field(ge=0)
    daily_active_users: int = Field(ge=0)
    weekly_active_users: int = Field(ge=0)
    monthly_active_users: int = Field(ge=0)
    active_user_percentage: float = Field(ge=0.0, le=100.0)
    average_conversations_per_user: float = Field(ge=0.0)
    average_questions_per_user: float = Field(ge=0.0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(
        cls,
        snapshot: UserAnalyticsOverviewSnapshot,
    ) -> UserAnalyticsOverviewResponse:
        """Build an API response from a service-layer overview."""
        return cls.model_validate(snapshot)


class UserGrowthTrendsResponse(BaseModel):
    """Time-series data for user growth and platform activity."""

    model_config = ConfigDict(from_attributes=True)

    user_registrations: ChartSeries
    active_users: ChartSeries
    login_activity: ChartSeries
    conversation_creation: ChartSeries
    questions_asked: ChartSeries
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(
        cls,
        snapshot: UserGrowthTrendsSnapshot,
    ) -> UserGrowthTrendsResponse:
        """Build an API response from a service-layer trends snapshot."""
        return cls.model_validate(snapshot)


class UserActivityResponse(BaseModel):
    """Engagement metrics and activity trend series."""

    model_config = ConfigDict(from_attributes=True)

    average_conversations_per_user: float = Field(ge=0.0)
    average_questions_per_user: float = Field(ge=0.0)
    average_engagement_score: float = Field(ge=0.0)
    active_users: ChartSeries
    questions_asked: ChartSeries
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: UserActivitySnapshot) -> UserActivityResponse:
        """Build an API response from a service-layer activity snapshot."""
        return cls.model_validate(snapshot)


class UserActivityItemResponse(BaseModel):
    """Single row in top or inactive user tables."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    conversation_count: int = Field(ge=0)
    question_count: int = Field(ge=0)
    last_active_at: datetime | None = None

    @classmethod
    def from_row(cls, row: object) -> UserActivityItemResponse:
        """Build a response row from a repository record."""
        return cls.model_validate(row)


class PaginatedUserActivityResponse(BaseModel):
    """Paginated user activity results."""

    items: list[UserActivityItemResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)

    @classmethod
    def from_rows(
        cls,
        rows: list[object],
        *,
        total: int,
        limit: int,
        offset: int,
    ) -> PaginatedUserActivityResponse:
        """Build a paginated response from repository rows."""
        return cls(
            items=[UserActivityItemResponse.from_row(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )
