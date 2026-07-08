"""Unit tests for reporting service (Phase 11.7)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.analytics.context import AnalyticsContext
from app.analytics.repositories.report_repository import ReportFormat, ReportModule, ReportRepository
from app.analytics.schemas.common import ChartSeries
from app.analytics.services.ai_analytics_service import AIAnalyticsOverviewSnapshot, AITrendsSnapshot
from app.analytics.services.reporting_service import ReportingService
from app.analytics.services.user_analytics_service import UserAnalyticsOverviewSnapshot, UserGrowthTrendsSnapshot


def _context() -> AnalyticsContext:
    return AnalyticsContext(
        start_date=datetime(2026, 6, 1, tzinfo=UTC),
        end_date=datetime(2026, 6, 24, tzinfo=UTC),
        timezone="UTC",
        group_by=None,
    )


def _empty_series(name: str) -> ChartSeries:
    return ChartSeries(event_type=name, points={})


class TestReportingService:
    def _build_service(self) -> tuple[ReportingService, MagicMock]:
        user_service = MagicMock()
        ai_service = MagicMock()
        knowledge_service = MagicMock()
        monitoring_service = MagicMock()
        error_service = MagicMock()

        service = ReportingService(
            report_repository=ReportRepository(),
            user_service=user_service,
            ai_service=ai_service,
            knowledge_service=knowledge_service,
            monitoring_service=monitoring_service,
            error_service=error_service,
        )
        return service, user_service

    def test_export_user_csv_uses_existing_analytics_services(self) -> None:
        service, user_service = self._build_service()
        context = _context()
        user_service.get_overview.return_value = UserAnalyticsOverviewSnapshot(
            total_users=10,
            new_users=2,
            daily_active_users=4,
            weekly_active_users=6,
            monthly_active_users=8,
            active_user_percentage=40.0,
            average_conversations_per_user=1.5,
            average_questions_per_user=3.0,
            start_date=context.start_date,
            end_date=context.end_date,
        )
        user_service.get_trends.return_value = UserGrowthTrendsSnapshot(
            user_registrations=_empty_series("user_registrations"),
            active_users=_empty_series("active_users"),
            login_activity=_empty_series("login_activity"),
            conversation_creation=_empty_series("conversation_creation"),
            questions_asked=_empty_series("questions_asked"),
            start_date=context.start_date,
            end_date=context.end_date,
        )
        user_service.get_top_users.return_value = ([], 0)
        user_service.get_inactive_users.return_value = ([], 0)

        result = service.export_report(
            module=ReportModule.USER,
            report_format=ReportFormat.CSV,
            context=context,
        )

        user_service.get_overview.assert_called_once_with(context)
        user_service.get_trends.assert_called_once_with(context)
        assert result.filename.endswith(".csv")
        assert result.media_type == "text/csv"
        assert b"User Analytics" in result.content

    def test_export_ai_pdf_filename_contains_module_and_dates(self) -> None:
        service, _ = self._build_service()
        context = _context()
        ai_service = service._ai_service
        ai_service.get_overview.return_value = AIAnalyticsOverviewSnapshot(
            total_questions=5,
            responses_generated=4,
            average_response_time_seconds=1.2,
            average_retrieval_time_seconds=None,
            average_retrieved_documents=2.0,
            citation_usage_rate=50.0,
            retrieval_success_rate=80.0,
            retrieval_failure_rate=20.0,
            ai_error_rate=10.0,
            average_confidence_score=0.8,
            start_date=context.start_date,
            end_date=context.end_date,
        )
        ai_service.get_trends.return_value = AITrendsSnapshot(
            questions=_empty_series("questions"),
            responses=_empty_series("responses"),
            retrieval_success=_empty_series("retrieval_success"),
            retrieval_failures=_empty_series("retrieval_failures"),
            average_response_time=_empty_series("average_response_time"),
            citation_usage=_empty_series("citation_usage"),
            start_date=context.start_date,
            end_date=context.end_date,
        )
        ai_service.get_retrieval.return_value = MagicMock(collection_distribution={})
        ai_service.get_questions.return_value = MagicMock(items=[])
        ai_service.get_failures.return_value = MagicMock(items=[])

        result = service.export_report(
            module=ReportModule.AI,
            report_format=ReportFormat.PDF,
            context=context,
        )

        assert result.filename == "ai_analytics_20260601_20260624.pdf"
        assert result.content.startswith(b"%PDF")

    def test_list_modules_and_formats_delegate_to_repository(self) -> None:
        service, _ = self._build_service()

        assert len(service.list_modules()) == 5
        assert len(service.list_formats()) == 3
