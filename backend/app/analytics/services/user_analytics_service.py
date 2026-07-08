"""User analytics orchestration for administrator dashboards (Phase 11.2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.analytics.repositories.user_repository import UserRepository
from app.analytics.schemas.common import ChartSeries
from app.analytics.utils.aggregation import bucket_counts_by_day
from app.analytics.utils.date_filters import (
    context_for_day,
    context_for_last_n_days,
)


@dataclass(frozen=True)
class UserAnalyticsOverviewSnapshot:
    """Service-layer user analytics KPI snapshot."""

    total_users: int
    new_users: int
    daily_active_users: int
    weekly_active_users: int
    monthly_active_users: int
    active_user_percentage: float
    average_conversations_per_user: float
    average_questions_per_user: float
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class UserGrowthTrendsSnapshot:
    """Service-layer user growth time-series snapshot."""

    user_registrations: ChartSeries
    active_users: ChartSeries
    login_activity: ChartSeries
    conversation_creation: ChartSeries
    questions_asked: ChartSeries
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class UserActivitySnapshot:
    """Service-layer user engagement activity snapshot."""

    average_conversations_per_user: float
    average_questions_per_user: float
    average_engagement_score: float
    active_users: ChartSeries
    questions_asked: ChartSeries
    start_date: datetime
    end_date: datetime


class UserAnalyticsService:
    """Aggregate user adoption, engagement, and activity metrics."""

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def get_overview(self, context: AnalyticsContext) -> UserAnalyticsOverviewSnapshot:
        """Return administrator KPIs for the reporting window."""
        anchor_end = context.end_date
        total_users = self._repository.count_total_users()
        period_active_users = self._repository.count_distinct_active_users(context)
        conversations = self._repository.count_conversations(context)
        questions = self._repository.count_questions(context)
        question_askers = self._repository.count_distinct_question_askers(context)

        active_pct = (
            (period_active_users / total_users) * 100.0 if total_users else 0.0
        )
        avg_conversations = (
            conversations / question_askers if question_askers else 0.0
        )
        avg_questions = questions / question_askers if question_askers else 0.0

        return UserAnalyticsOverviewSnapshot(
            total_users=total_users,
            new_users=self._repository.count_new_users(context),
            daily_active_users=self._repository.count_distinct_active_users(
                context_for_day(anchor_end),
            ),
            weekly_active_users=self._repository.count_distinct_active_users(
                context_for_last_n_days(7, end=anchor_end),
            ),
            monthly_active_users=self._repository.count_distinct_active_users(
                context_for_last_n_days(30, end=anchor_end),
            ),
            active_user_percentage=round(active_pct, 2),
            average_conversations_per_user=round(avg_conversations, 2),
            average_questions_per_user=round(avg_questions, 2),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_trends(self, context: AnalyticsContext) -> UserGrowthTrendsSnapshot:
        """Return user growth and activity time-series for charting."""
        return UserGrowthTrendsSnapshot(
            user_registrations=self._build_series(
                "user_registrations",
                bucket_counts_by_day(
                    self._repository.list_user_registration_timestamps(context),
                ),
            ),
            active_users=self._build_series(
                "active_users",
                bucket_counts_by_day(
                    self._repository.list_active_user_timestamps(context),
                ),
            ),
            login_activity=self._build_series(
                AnalyticsEvents.LOGIN_SUCCESS,
                bucket_counts_by_day(
                    self._repository.list_event_timestamps(
                        AnalyticsEvents.LOGIN_SUCCESS,
                        context,
                    ),
                ),
            ),
            conversation_creation=self._build_series(
                "conversation_creation",
                bucket_counts_by_day(
                    self._repository.list_conversation_timestamps(context),
                ),
            ),
            questions_asked=self._build_series(
                AnalyticsEvents.CHAT_QUESTION,
                bucket_counts_by_day(
                    self._repository.list_event_timestamps(
                        AnalyticsEvents.CHAT_QUESTION,
                        context,
                    ),
                ),
            ),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_activity(self, context: AnalyticsContext) -> UserActivitySnapshot:
        """Return engagement metrics and activity trend series."""
        overview = self.get_overview(context)
        engagement_score = round(
            (overview.average_conversations_per_user + overview.average_questions_per_user)
            / 2.0,
            2,
        )
        trends = self.get_trends(context)
        return UserActivitySnapshot(
            average_conversations_per_user=overview.average_conversations_per_user,
            average_questions_per_user=overview.average_questions_per_user,
            average_engagement_score=engagement_score,
            active_users=trends.active_users,
            questions_asked=trends.questions_asked,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_top_users(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list, int]:
        """Return users ranked by activity in *context*."""
        return self._repository.list_top_active_users(
            context,
            limit=limit,
            offset=offset,
        )

    def get_inactive_users(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list, int]:
        """Return active accounts with no audit activity in *context*."""
        return self._repository.list_inactive_users(
            context,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def _build_series(event_type: str, points: dict[str, int]) -> ChartSeries:
        return ChartSeries(event_type=event_type, points=points)


def build_user_analytics_service(db: Session) -> UserAnalyticsService:
    """Construct a user analytics service bound to the given database session."""
    return UserAnalyticsService(UserRepository(db))
