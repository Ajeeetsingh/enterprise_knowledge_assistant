"""AI analytics orchestration for administrator dashboards (Phase 11.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.analytics.repositories.ai_repository import AIRepository
from app.analytics.schemas.common import ChartSeries
from app.analytics.utils.aggregation import average, bucket_counts_by_day, extract_metadata_values


@dataclass(frozen=True)
class AIAnalyticsOverviewSnapshot:
    """Service-layer AI analytics KPI snapshot."""

    total_questions: int
    responses_generated: int
    average_response_time_seconds: float | None
    average_retrieval_time_seconds: float | None
    average_retrieved_documents: float | None
    citation_usage_rate: float
    retrieval_success_rate: float
    retrieval_failure_rate: float
    ai_error_rate: float
    average_confidence_score: float | None
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class AITrendsSnapshot:
    """Service-layer AI trend series snapshot."""

    questions: ChartSeries
    responses: ChartSeries
    retrieval_success: ChartSeries
    retrieval_failures: ChartSeries
    average_response_time: ChartSeries
    citation_usage: ChartSeries
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class AIRetrievalSnapshot:
    """Service-layer retrieval analytics snapshot."""

    average_retrieved_chunks: float | None
    average_retrieval_latency_seconds: float | None
    retrieval_success_percentage: float
    empty_retrievals: int
    collection_distribution: dict[str, int]
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class AIQualitySnapshot:
    """Service-layer AI quality analytics snapshot."""

    items: list[dict[str, object]]
    total: int
    average_citations_per_response: float | None
    responses_without_citations: int
    questions_without_documents: int
    quality_summary: str
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class AIFailureAnalyticsSnapshot:
    """Service-layer failure analytics snapshot."""

    items: list[dict[str, object]]
    total: int
    limit: int
    offset: int
    start_date: datetime
    end_date: datetime


class AIAnalyticsService:
    """Aggregate AI performance, retrieval, and quality metrics."""

    def __init__(self, repository: AIRepository) -> None:
        self._repository = repository

    def get_overview(self, context: AnalyticsContext) -> AIAnalyticsOverviewSnapshot:
        """Return administrator KPIs for AI assistant performance."""
        questions = self._repository.count_questions(context)
        responses = self._repository.count_responses(context)
        failures = self._repository.count_failures(context)
        attempts = responses + failures

        citation_values = extract_metadata_values(
            self._repository.get_answer_metadata(context),
            "citation_count",
        )
        cited_responses = sum(1 for value in citation_values if value > 0)
        citation_rate = (cited_responses / responses * 100.0) if responses else 0.0
        success_rate = (responses / attempts * 100.0) if attempts else 0.0
        failure_rate = (failures / attempts * 100.0) if attempts else 0.0
        error_rate = (failures / questions * 100.0) if questions else 0.0

        response_times = self._repository.compute_response_time_seconds(context)
        avg_response_time = average(response_times)

        return AIAnalyticsOverviewSnapshot(
            total_questions=questions,
            responses_generated=responses,
            average_response_time_seconds=(
                round(avg_response_time, 2) if avg_response_time is not None else None
            ),
            average_retrieval_time_seconds=None,
            average_retrieved_documents=self._repository.average_citation_count(context),
            citation_usage_rate=round(citation_rate, 2),
            retrieval_success_rate=round(success_rate, 2),
            retrieval_failure_rate=round(failure_rate, 2),
            ai_error_rate=round(error_rate, 2),
            average_confidence_score=self._repository.average_confidence_score(context),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_trends(self, context: AnalyticsContext) -> AITrendsSnapshot:
        """Return AI activity and performance time-series."""
        response_samples = self._repository.compute_response_time_samples(context)
        citation_rows = self._repository.get_answer_metadata_with_timestamps(context)

        return AITrendsSnapshot(
            questions=self._series(
                AnalyticsEvents.CHAT_QUESTION,
                bucket_counts_by_day(
                    self._repository.list_event_timestamps(
                        AnalyticsEvents.CHAT_QUESTION,
                        context,
                    )
                ),
            ),
            responses=self._series(
                AnalyticsEvents.CHAT_RESPONSE,
                bucket_counts_by_day(
                    self._repository.list_event_timestamps(
                        AnalyticsEvents.CHAT_RESPONSE,
                        context,
                    )
                ),
            ),
            retrieval_success=self._series(
                "retrieval_success",
                bucket_counts_by_day(
                    self._repository.list_event_timestamps(
                        AnalyticsEvents.CHAT_RESPONSE,
                        context,
                    )
                ),
            ),
            retrieval_failures=self._series(
                AnalyticsEvents.CHAT_FAILURE,
                bucket_counts_by_day(
                    self._repository.list_event_timestamps(
                        AnalyticsEvents.CHAT_FAILURE,
                        context,
                    )
                ),
            ),
            average_response_time=self._series(
                "average_response_time_seconds",
                self._bucket_average_response_times(response_samples),
            ),
            citation_usage=self._series(
                "citation_usage",
                self._bucket_citation_usage(citation_rows),
            ),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_retrieval(self, context: AnalyticsContext) -> AIRetrievalSnapshot:
        """Return retrieval-focused analytics."""
        overview = self.get_overview(context)
        return AIRetrievalSnapshot(
            average_retrieved_chunks=overview.average_retrieved_documents,
            average_retrieval_latency_seconds=overview.average_retrieval_time_seconds,
            retrieval_success_percentage=overview.retrieval_success_rate,
            empty_retrievals=self._repository.count_empty_retrievals(context),
            collection_distribution=self._repository.citation_source_distribution(context),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_questions(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> AIQualitySnapshot:
        """Return recurring question and quality analytics."""
        rows, total = self._repository.list_top_questions(
            context,
            limit=limit,
            offset=offset,
        )
        responses = self._repository.count_responses(context)
        without_citations = self._repository.count_responses_without_citations(context)
        avg_citations = self._repository.average_citation_count(context)
        confidence = self._repository.average_confidence_score(context)

        summary_parts = [
            f"{responses} responses generated",
            f"{without_citations} responses without citations",
        ]
        if confidence is not None:
            summary_parts.append(f"average confidence {confidence:.2f}")

        return AIQualitySnapshot(
            items=[{"question": row.question, "count": row.count} for row in rows],
            total=total,
            average_citations_per_response=avg_citations,
            responses_without_citations=without_citations,
            questions_without_documents=without_citations,
            quality_summary="; ".join(summary_parts),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_failures(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> AIFailureAnalyticsSnapshot:
        """Return aggregated retrieval failure analytics."""
        rows, total = self._repository.list_failure_reasons(
            context,
            limit=limit,
            offset=offset,
        )
        return AIFailureAnalyticsSnapshot(
            items=[{"reason": row.reason, "count": row.count} for row in rows],
            total=total,
            limit=limit,
            offset=offset,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    @staticmethod
    def _series(event_type: str, points: dict[str, float | int]) -> ChartSeries:
        normalized = {key: int(value) for key, value in points.items()}
        return ChartSeries(event_type=event_type, points=normalized)

    @staticmethod
    def _bucket_average_response_times(
        samples: list[tuple[datetime, float]],
    ) -> dict[str, int]:
        if not samples:
            return {}
        buckets: dict[str, list[float]] = {}
        for timestamp, seconds in samples:
            day = timestamp.astimezone(UTC).date().isoformat()
            buckets.setdefault(day, []).append(seconds)
        return {
            day: int(round(sum(values) / len(values)))
            for day, values in sorted(buckets.items())
        }

    @staticmethod
    def _bucket_citation_usage(
        rows: list[tuple[datetime, dict]],
    ) -> dict[str, int]:
        counter: dict[str, int] = {}
        for timestamp, metadata in rows:
            if int(metadata.get("citation_count") or 0) <= 0:
                continue
            day = timestamp.astimezone(UTC).date().isoformat()
            counter[day] = counter.get(day, 0) + 1
        return dict(sorted(counter.items()))


def build_ai_analytics_service(db: Session) -> AIAnalyticsService:
    """Construct an AI analytics service bound to the given database session."""
    return AIAnalyticsService(AIRepository(db))
