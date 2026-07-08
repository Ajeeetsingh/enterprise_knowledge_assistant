"""Analytics reporting orchestration for administrator exports (Phase 11.7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.context import AnalyticsContext
from app.analytics.exporters.csv_exporter import CSVReportExporter
from app.analytics.exporters.excel_exporter import ExcelReportExporter
from app.analytics.exporters.pdf_exporter import PDFReportExporter
from app.analytics.repositories.report_repository import (
    ReportFormat,
    ReportModule,
    ReportRepository,
)
from app.analytics.services.ai_analytics_service import AIAnalyticsService, build_ai_analytics_service
from app.analytics.services.error_analytics_service import (
    ErrorAnalyticsService,
    build_error_analytics_service,
)
from app.analytics.services.knowledge_analytics_service import (
    KnowledgeAnalyticsService,
    build_knowledge_analytics_service,
)
from app.analytics.services.monitoring_service import (
    SystemMonitoringAnalyticsService,
    build_system_monitoring_analytics_service,
)
from app.analytics.services.report_payload import (
    AnalyticsReportPayload,
    chart_series_to_trend,
    dataclass_rows_to_table,
    dict_to_table,
    items_to_table,
    snapshot_to_kpis,
)
from app.analytics.services.user_analytics_service import UserAnalyticsService, build_user_analytics_service

DEFAULT_REPORT_TABLE_LIMIT = 50


@dataclass(frozen=True)
class ReportExportResult:
    """Binary export artifact returned to API handlers."""

    content: bytes
    filename: str
    media_type: str


class ReportingService:
    """Build analytics reports by reusing existing analytics services."""

    def __init__(
        self,
        *,
        report_repository: ReportRepository,
        user_service: UserAnalyticsService,
        ai_service: AIAnalyticsService,
        knowledge_service: KnowledgeAnalyticsService,
        monitoring_service: SystemMonitoringAnalyticsService,
        error_service: ErrorAnalyticsService,
    ) -> None:
        self._report_repository = report_repository
        self._user_service = user_service
        self._ai_service = ai_service
        self._knowledge_service = knowledge_service
        self._monitoring_service = monitoring_service
        self._error_service = error_service
        self._exporters = {
            ReportFormat.CSV: CSVReportExporter(),
            ReportFormat.XLSX: ExcelReportExporter(),
            ReportFormat.PDF: PDFReportExporter(),
        }

    def list_modules(self) -> list:
        """Return exportable analytics modules."""
        return self._report_repository.list_modules()

    def list_formats(self) -> list:
        """Return supported export formats."""
        return self._report_repository.list_formats()

    def export_report(
        self,
        *,
        module: ReportModule,
        report_format: ReportFormat,
        context: AnalyticsContext,
        table_limit: int = DEFAULT_REPORT_TABLE_LIMIT,
    ) -> ReportExportResult:
        """Generate a report file for the requested module and format."""
        module_definition = self._report_repository.get_module(module)
        format_definition = self._report_repository.get_format(report_format)
        payload = self._build_payload(
            module=module,
            module_title=module_definition.title,
            context=context,
            table_limit=table_limit,
        )
        exporter = self._exporters[report_format]
        content = exporter.export(payload)
        filename = self._build_filename(
            module=module.value,
            start_date=payload.start_date,
            end_date=payload.end_date,
            extension=format_definition.extension,
        )
        return ReportExportResult(
            content=content,
            filename=filename,
            media_type=format_definition.media_type,
        )

    def _build_payload(
        self,
        *,
        module: ReportModule,
        module_title: str,
        context: AnalyticsContext,
        table_limit: int,
    ) -> AnalyticsReportPayload:
        builders = {
            ReportModule.USER: self._build_user_payload,
            ReportModule.AI: self._build_ai_payload,
            ReportModule.KNOWLEDGE: self._build_knowledge_payload,
            ReportModule.MONITORING: self._build_monitoring_payload,
            ReportModule.ERRORS: self._build_error_payload,
        }
        kpis, tables, trends = builders[module](context, table_limit)
        return AnalyticsReportPayload(
            module=module.value,
            module_title=module_title,
            generated_at=datetime.now(tz=UTC),
            start_date=context.start_date,
            end_date=context.end_date,
            kpis=kpis,
            tables=tables,
            trends=trends,
        )

    def _build_user_payload(
        self,
        context: AnalyticsContext,
        table_limit: int,
    ) -> tuple[tuple[tuple[str, str], ...], tuple, tuple]:
        overview = self._user_service.get_overview(context)
        trends_snapshot = self._user_service.get_trends(context)
        top_users, _ = self._user_service.get_top_users(
            context,
            limit=table_limit,
        )
        inactive_users, _ = self._user_service.get_inactive_users(
            context,
            limit=table_limit,
        )

        kpis = snapshot_to_kpis(overview)
        tables = (
            dataclass_rows_to_table(
                "Top Active Users",
                top_users,
                column_order=(
                    "email",
                    "full_name",
                    "conversation_count",
                    "question_count",
                    "last_active_at",
                ),
            ),
            dataclass_rows_to_table(
                "Inactive Users",
                inactive_users,
                column_order=("email", "full_name", "is_active", "last_active_at"),
            ),
        )
        trend_sections = (
            chart_series_to_trend("User Registrations", trends_snapshot.user_registrations),
            chart_series_to_trend("Active Users", trends_snapshot.active_users),
            chart_series_to_trend("Login Activity", trends_snapshot.login_activity),
            chart_series_to_trend("Conversation Creation", trends_snapshot.conversation_creation),
            chart_series_to_trend("Questions Asked", trends_snapshot.questions_asked),
        )
        return kpis, tables, trend_sections

    def _build_ai_payload(
        self,
        context: AnalyticsContext,
        table_limit: int,
    ) -> tuple[tuple[tuple[str, str], ...], tuple, tuple]:
        overview = self._ai_service.get_overview(context)
        trends_snapshot = self._ai_service.get_trends(context)
        retrieval = self._ai_service.get_retrieval(context)
        questions = self._ai_service.get_questions(context, limit=table_limit)
        failures = self._ai_service.get_failures(context, limit=table_limit)

        kpis = snapshot_to_kpis(overview)
        tables = (
            dict_to_table("Collection Distribution", retrieval.collection_distribution),
            items_to_table("Top Questions", questions.items),
            items_to_table("Failure Reasons", failures.items),
        )
        trend_sections = (
            chart_series_to_trend("Questions", trends_snapshot.questions),
            chart_series_to_trend("Responses", trends_snapshot.responses),
            chart_series_to_trend("Retrieval Success", trends_snapshot.retrieval_success),
            chart_series_to_trend("Retrieval Failures", trends_snapshot.retrieval_failures),
            chart_series_to_trend("Average Response Time", trends_snapshot.average_response_time),
            chart_series_to_trend("Citation Usage", trends_snapshot.citation_usage),
        )
        return kpis, tables, trend_sections

    def _build_knowledge_payload(
        self,
        context: AnalyticsContext,
        table_limit: int,
    ) -> tuple[tuple[tuple[str, str], ...], tuple, tuple]:
        overview = self._knowledge_service.get_overview(context)
        documents = self._knowledge_service.get_documents(context, limit=table_limit)
        collections = self._knowledge_service.get_collections(context, limit=table_limit)
        searches = self._knowledge_service.get_searches(context, limit=table_limit)
        gaps = self._knowledge_service.get_gaps(context, limit=table_limit)
        freshness = self._knowledge_service.get_freshness(context, limit=table_limit)

        kpis = snapshot_to_kpis(overview)
        tables = (
            items_to_table("Most Viewed Documents", documents.most_viewed),
            items_to_table("Least Viewed Documents", documents.least_viewed),
            items_to_table("Collection Usage", collections.items),
            dict_to_table("Collection Popularity", collections.collection_popularity),
            items_to_table("Search Topics", searches.topics),
            items_to_table("Searched Documents", searches.documents),
            items_to_table("Knowledge Gaps", gaps.items),
            items_to_table("Recent Uploads", freshness.recent_uploads),
            items_to_table("Oldest Documents", freshness.oldest_documents),
            items_to_table("Recently Updated Documents", freshness.recently_updated),
            items_to_table("Longest Inactive Documents", freshness.longest_inactive),
        )
        trend_sections = (
            chart_series_to_trend(
                "Document Usage Trend",
                documents.document_usage_trend,
            ),
            chart_series_to_trend("Upload Trend", freshness.upload_trend),
            chart_series_to_trend("Search Trend", searches.search_trend),
        )
        return kpis, tables, trend_sections

    def _build_monitoring_payload(
        self,
        context: AnalyticsContext,
        table_limit: int,
    ) -> tuple[tuple[tuple[str, str], ...], tuple, tuple]:
        overview = self._monitoring_service.get_overview(context)
        performance = self._monitoring_service.get_performance(context)
        resources = self._monitoring_service.get_resources(context)
        services = self._monitoring_service.get_services(context)
        trends_snapshot = self._monitoring_service.get_trends(
            context,
            limit=table_limit,
        )

        kpis = snapshot_to_kpis(overview) + snapshot_to_kpis(performance) + snapshot_to_kpis(resources)
        tables = (items_to_table("Service Status", services.items),)
        if trends_snapshot.timeline_items:
            tables = tables + (
                items_to_table("Health Timeline", trends_snapshot.timeline_items),
            )
        trend_sections = (
            chart_series_to_trend("API Latency", trends_snapshot.api_latency),
            chart_series_to_trend("Search Latency", trends_snapshot.search_latency),
            chart_series_to_trend("Errors", trends_snapshot.errors),
            chart_series_to_trend("Health Events", trends_snapshot.health_events),
        )
        return kpis, tables, trend_sections

    def _build_error_payload(
        self,
        context: AnalyticsContext,
        table_limit: int,
    ) -> tuple[tuple[tuple[str, str], ...], tuple, tuple]:
        overview = self._error_service.get_overview(context)
        trends_snapshot = self._error_service.get_trends(context)
        categories = self._error_service.get_categories(context, limit=table_limit)
        endpoints = self._error_service.get_endpoints(context, limit=table_limit)
        failures = self._error_service.get_failures(context, limit=table_limit)

        kpis = snapshot_to_kpis(overview)
        tables = (
            dict_to_table("Errors By Category", categories.by_category),
            dict_to_table("Errors By Service", categories.by_service),
            items_to_table("Recurring Errors", categories.recurring_errors),
            items_to_table("Endpoint Failures", endpoints.items),
            items_to_table("Failed Operations", failures.failed_operations),
            items_to_table("Retrieval Failures", failures.retrieval_failures),
            items_to_table("Upload Failures", failures.upload_failures),
            items_to_table("Authentication Failures", failures.authentication_failures),
        )
        if categories.by_severity is not None:
            tables = (dict_to_table("Errors By Severity", categories.by_severity),) + tables
        trend_sections = (
            chart_series_to_trend("Total Errors", trends_snapshot.total_errors),
            chart_series_to_trend(
                "Authentication Failures",
                trends_snapshot.authentication_failures,
            ),
            chart_series_to_trend("Retrieval Failures", trends_snapshot.retrieval_failures),
            chart_series_to_trend("Upload Failures", trends_snapshot.upload_failures),
            chart_series_to_trend("API Exceptions", trends_snapshot.api_exceptions),
            chart_series_to_trend("Permission Denials", trends_snapshot.permission_denials),
        )
        return kpis, tables, trend_sections

    @staticmethod
    def _build_filename(
        *,
        module: str,
        start_date: datetime,
        end_date: datetime,
        extension: str,
    ) -> str:
        start_label = start_date.astimezone(UTC).strftime("%Y%m%d")
        end_label = end_date.astimezone(UTC).strftime("%Y%m%d")
        return f"{module}_analytics_{start_label}_{end_label}.{extension}"


def build_reporting_service(db: Session) -> ReportingService:
    """Construct a reporting service bound to the given database session."""
    return ReportingService(
        report_repository=ReportRepository(),
        user_service=build_user_analytics_service(db),
        ai_service=build_ai_analytics_service(db),
        knowledge_service=build_knowledge_analytics_service(db),
        monitoring_service=build_system_monitoring_analytics_service(db),
        error_service=build_error_analytics_service(db),
    )
