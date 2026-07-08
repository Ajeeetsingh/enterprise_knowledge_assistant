"""Error analytics orchestration for administrator dashboards (Phase 11.6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.analytics.repositories.error_repository import ErrorAnalyticsRepository
from app.analytics.schemas.common import ChartSeries
from app.analytics.utils.aggregation import bucket_counts_by_day


@dataclass(frozen=True)
class ErrorOverviewSnapshot:
    """Service-layer error analytics KPI snapshot."""

    total_errors: int
    authentication_failures: int
    authorization_failures: int
    upload_failures: int | None
    indexing_failures: int | None
    retrieval_failures: int
    api_errors: int | None
    background_job_failures: int | None
    error_rate: float
    error_free_requests_percentage: float
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class ErrorTrendsSnapshot:
    """Service-layer error trend series snapshot."""

    total_errors: ChartSeries
    authentication_failures: ChartSeries
    retrieval_failures: ChartSeries
    upload_failures: ChartSeries
    api_exceptions: ChartSeries
    permission_denials: ChartSeries
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class ErrorCategorySnapshot:
    """Service-layer error breakdown snapshot."""

    by_category: dict[str, int]
    by_service: dict[str, int]
    by_severity: dict[str, int] | None
    recurring_errors: list[dict[str, object]]
    total_recurring_errors: int
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class EndpointFailureSnapshot:
    """Service-layer endpoint failure snapshot."""

    items: list[dict[str, object]]
    total: int
    limit: int
    offset: int
    start_date: datetime
    end_date: datetime


@dataclass(frozen=True)
class FailureAnalysisSnapshot:
    """Service-layer failure analysis snapshot."""

    failed_operations: list[dict[str, object]]
    retrieval_failures: list[dict[str, object]]
    upload_failures: list[dict[str, object]]
    authentication_failures: list[dict[str, object]]
    total_failed_operations: int
    total_retrieval_failures: int
    total_upload_failures: int
    total_authentication_failures: int
    limit: int
    offset: int
    start_date: datetime
    end_date: datetime


class ErrorAnalyticsService:
    """Aggregate operational failures and recurring error patterns."""

    def __init__(self, repository: ErrorAnalyticsRepository) -> None:
        self._repository = repository

    def get_overview(self, context: AnalyticsContext) -> ErrorOverviewSnapshot:
        """Return administrator KPIs for operational failures."""
        total_errors = self._repository.count_total_errors(context)
        total_events = self._repository.count_total_audit_events(context)
        error_rate = (total_errors / total_events * 100.0) if total_events else 0.0
        error_free = max(100.0 - error_rate, 0.0)

        return ErrorOverviewSnapshot(
            total_errors=total_errors,
            authentication_failures=self._repository.count_authentication_failures(context),
            authorization_failures=self._repository.count_authorization_failures(context),
            upload_failures=self._repository.count_upload_failures(context),
            indexing_failures=self._repository.count_indexing_failures(context),
            retrieval_failures=self._repository.count_retrieval_failures(context),
            api_errors=self._repository.count_api_errors(context),
            background_job_failures=self._repository.count_background_job_failures(context),
            error_rate=round(error_rate, 2),
            error_free_requests_percentage=round(error_free, 2),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_trends(self, context: AnalyticsContext) -> ErrorTrendsSnapshot:
        """Return error trend series for the selected reporting window."""
        return ErrorTrendsSnapshot(
            total_errors=self._series(
                "total_errors",
                bucket_counts_by_day(self._repository.list_failed_event_timestamps(context)),
            ),
            authentication_failures=self._series(
                AnalyticsEvents.LOGIN_FAILED,
                bucket_counts_by_day(
                    self._repository.list_authentication_failure_timestamps(context),
                ),
            ),
            retrieval_failures=self._series(
                AnalyticsEvents.CHAT_FAILURE,
                bucket_counts_by_day(
                    self._repository.list_retrieval_failure_timestamps(context),
                ),
            ),
            upload_failures=self._series(
                "upload_failures",
                bucket_counts_by_day(
                    self._repository.list_upload_failure_timestamps(context),
                ),
            ),
            api_exceptions=self._series("api_exceptions", {}),
            permission_denials=self._series(
                AnalyticsEvents.SECURITY_PERMISSION_DENIED,
                bucket_counts_by_day(
                    self._repository.list_permission_denial_timestamps(context),
                ),
            ),
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_categories(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> ErrorCategorySnapshot:
        """Return error breakdown by category and recurring patterns."""
        rows, total = self._repository.list_recurring_errors(
            context,
            limit=limit,
            offset=offset,
        )
        return ErrorCategorySnapshot(
            by_category=self._repository.errors_by_category(context),
            by_service=self._repository.errors_by_service(context),
            by_severity=None,
            recurring_errors=[self._error_row(row) for row in rows],
            total_recurring_errors=total,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_endpoints(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> EndpointFailureSnapshot:
        """Return endpoint failure analytics."""
        rows, total = self._repository.list_endpoint_failures(
            context,
            limit=limit,
            offset=offset,
        )
        return EndpointFailureSnapshot(
            items=[self._endpoint_row(row) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
            start_date=context.start_date,
            end_date=context.end_date,
        )

    def get_failures(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> FailureAnalysisSnapshot:
        """Return measurable failure analysis sections."""
        operations, total_operations = self._repository.list_failed_operations(
            context,
            limit=limit,
            offset=offset,
        )
        retrieval, total_retrieval = self._repository.list_retrieval_failure_reasons(
            context,
            limit=limit,
            offset=offset,
        )
        uploads, total_uploads = self._repository.list_upload_failure_details(
            context,
            limit=limit,
            offset=offset,
        )
        auth, total_auth = self._repository.list_authentication_failure_details(
            context,
            limit=limit,
            offset=offset,
        )
        return FailureAnalysisSnapshot(
            failed_operations=[self._error_row(row) for row in operations],
            retrieval_failures=[self._error_row(row) for row in retrieval],
            upload_failures=[self._error_row(row) for row in uploads],
            authentication_failures=[self._error_row(row) for row in auth],
            total_failed_operations=total_operations,
            total_retrieval_failures=total_retrieval,
            total_upload_failures=total_uploads,
            total_authentication_failures=total_auth,
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
    def _error_row(row: object) -> dict[str, object]:
        return {
            "label": row.label,
            "count": row.count,
            "category": row.category,
        }

    @staticmethod
    def _endpoint_row(row: object) -> dict[str, object]:
        return {
            "endpoint": row.endpoint,
            "count": row.count,
            "service": row.service,
        }


def build_error_analytics_service(db: Session) -> ErrorAnalyticsService:
    """Construct an error analytics service bound to the given database session."""
    return ErrorAnalyticsService(ErrorAnalyticsRepository(db))
