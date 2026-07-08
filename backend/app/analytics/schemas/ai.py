"""Pydantic models for AI analytics APIs (Phase 11.3)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.schemas.common import ChartSeries

if TYPE_CHECKING:
    from app.analytics.services.ai_analytics_service import (
        AIFailureAnalyticsSnapshot,
        AIQualitySnapshot,
        AIAnalyticsOverviewSnapshot,
        AIRetrievalSnapshot,
        AITrendsSnapshot,
    )


class AIAnalyticsOverviewResponse(BaseModel):
    """Administrator KPI summary for AI assistant performance."""

    model_config = ConfigDict(from_attributes=True)

    total_questions: int = Field(ge=0)
    responses_generated: int = Field(ge=0)
    average_response_time_seconds: float | None = Field(default=None, ge=0.0)
    average_retrieval_time_seconds: float | None = Field(default=None, ge=0.0)
    average_retrieved_documents: float | None = Field(default=None, ge=0.0)
    citation_usage_rate: float = Field(ge=0.0, le=100.0)
    retrieval_success_rate: float = Field(ge=0.0, le=100.0)
    retrieval_failure_rate: float = Field(ge=0.0, le=100.0)
    ai_error_rate: float = Field(ge=0.0, le=100.0)
    average_confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(
        cls,
        snapshot: AIAnalyticsOverviewSnapshot,
    ) -> AIAnalyticsOverviewResponse:
        """Build an API response from a service-layer overview."""
        return cls.model_validate(snapshot)


class AITrendsResponse(BaseModel):
    """Time-series data for AI activity and performance."""

    model_config = ConfigDict(from_attributes=True)

    questions: ChartSeries
    responses: ChartSeries
    retrieval_success: ChartSeries
    retrieval_failures: ChartSeries
    average_response_time: ChartSeries
    citation_usage: ChartSeries
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: AITrendsSnapshot) -> AITrendsResponse:
        """Build an API response from a service-layer trends snapshot."""
        return cls.model_validate(snapshot)


class AIRetrievalResponse(BaseModel):
    """Retrieval-focused analytics summary."""

    model_config = ConfigDict(from_attributes=True)

    average_retrieved_chunks: float | None = Field(default=None, ge=0.0)
    average_retrieval_latency_seconds: float | None = Field(default=None, ge=0.0)
    retrieval_success_percentage: float = Field(ge=0.0, le=100.0)
    empty_retrievals: int = Field(ge=0)
    collection_distribution: dict[str, int] = Field(default_factory=dict)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: AIRetrievalSnapshot) -> AIRetrievalResponse:
        """Build an API response from a service-layer retrieval snapshot."""
        return cls.model_validate(snapshot)


class QuestionFrequencyItemResponse(BaseModel):
    """Single row in top-questions analytics."""

    question: str
    count: int = Field(ge=1)


class AIQuestionsResponse(BaseModel):
    """Quality analytics for recurring user questions."""

    model_config = ConfigDict(from_attributes=True)

    items: list[QuestionFrequencyItemResponse]
    total: int = Field(ge=0)
    average_citations_per_response: float | None = Field(default=None, ge=0.0)
    responses_without_citations: int = Field(ge=0)
    questions_without_documents: int = Field(ge=0)
    quality_summary: str
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: AIQualitySnapshot) -> AIQuestionsResponse:
        """Build an API response from a service-layer quality snapshot."""
        return cls.model_validate(snapshot)


class FailureAnalysisItemResponse(BaseModel):
    """Single row in failure analysis analytics."""

    reason: str
    count: int = Field(ge=1)


class AIFailuresResponse(BaseModel):
    """Aggregated retrieval failure analytics."""

    model_config = ConfigDict(from_attributes=True)

    items: list[FailureAnalysisItemResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    start_date: datetime
    end_date: datetime

    @classmethod
    def from_snapshot(cls, snapshot: AIFailureAnalyticsSnapshot) -> AIFailuresResponse:
        """Build an API response from a service-layer failure snapshot."""
        return cls.model_validate(snapshot)
