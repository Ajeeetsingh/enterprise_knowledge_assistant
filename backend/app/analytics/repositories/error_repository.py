"""Read-only error analytics queries over persisted audit and document data."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.db.models.audit_log import AuditLog
from app.db.models.document import Document
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter
from app.documents.status import DocumentStatus


AUTHORIZATION_EVENT_TYPES = (
    AnalyticsEvents.SECURITY_PERMISSION_DENIED,
    AnalyticsEvents.SECURITY_INVALID_TOKEN,
    AnalyticsEvents.SECURITY_UNAUTHORIZED_ACCESS,
)


@dataclass(frozen=True)
class ErrorFrequencyRow:
    """Aggregated count for a recurring error label."""

    label: str
    count: int
    category: str


@dataclass(frozen=True)
class EndpointFailureRow:
    """Aggregated failure count for an endpoint or resource identifier."""

    endpoint: str
    count: int
    service: str


class ErrorAnalyticsRepository:
    """Persistence queries for operational error analytics."""

    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100

    def __init__(
        self,
        db: Session,
        *,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self._db = db
        self._audit_repository = audit_repository or AuditRepository(db)

    def count_total_errors(self, context: AnalyticsContext) -> int:
        """Return failed audit events within *context*."""
        return self._count_failed_events(context)

    def count_authentication_failures(self, context: AnalyticsContext) -> int:
        return self._count_events(AnalyticsEvents.LOGIN_FAILED, context)

    def count_authorization_failures(self, context: AnalyticsContext) -> int:
        return sum(
            self._count_events(event_type, context)
            for event_type in AUTHORIZATION_EVENT_TYPES
        )

    def count_upload_failures(self, context: AnalyticsContext) -> int | None:
        """Return upload failures when document lifecycle status is persisted."""
        return self._count_failed_documents(context)

    def count_indexing_failures(self, context: AnalyticsContext) -> int | None:
        """Return indexing failures derived from failed document lifecycle status."""
        return self._count_failed_documents(context)

    def count_retrieval_failures(self, context: AnalyticsContext) -> int:
        return self._count_events(AnalyticsEvents.CHAT_FAILURE, context)

    def count_api_errors(self, context: AnalyticsContext) -> int | None:
        """API exception metrics are not yet persisted in audit records."""
        return None

    def count_background_job_failures(self, context: AnalyticsContext) -> int | None:
        """Background worker failures are not yet instrumented."""
        return None

    def count_total_audit_events(self, context: AnalyticsContext) -> int:
        return self._audit_repository.count(
            filters=AuditSearchFilter(
                date_from=context.start_date,
                date_to=context.end_date,
            )
        )

    def list_failed_event_timestamps(self, context: AnalyticsContext) -> list[datetime]:
        return self._list_event_timestamps(context, status=AuditStatus.FAILED.value)

    def list_authentication_failure_timestamps(
        self,
        context: AnalyticsContext,
    ) -> list[datetime]:
        return self._list_event_timestamps(
            context,
            event_type=AnalyticsEvents.LOGIN_FAILED,
        )

    def list_retrieval_failure_timestamps(
        self,
        context: AnalyticsContext,
    ) -> list[datetime]:
        return self._list_event_timestamps(
            context,
            event_type=AnalyticsEvents.CHAT_FAILURE,
        )

    def list_permission_denial_timestamps(
        self,
        context: AnalyticsContext,
    ) -> list[datetime]:
        return self._list_event_timestamps(
            context,
            event_type=AnalyticsEvents.SECURITY_PERMISSION_DENIED,
        )

    def list_upload_failure_timestamps(
        self,
        context: AnalyticsContext,
    ) -> list[datetime]:
        query = (
            select(Document.updated_at)
            .where(Document.status == DocumentStatus.FAILED.value)
            .where(Document.updated_at >= context.start_date)
            .where(Document.updated_at <= context.end_date)
            .order_by(Document.updated_at.asc())
        )
        return list(self._db.scalars(query))

    def errors_by_category(self, context: AnalyticsContext) -> dict[str, int]:
        query = (
            select(AuditLog.event_category, func.count())
            .where(AuditLog.status == AuditStatus.FAILED.value)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .group_by(AuditLog.event_category)
        )
        rows = self._db.execute(query).all()
        return {str(category): int(count) for category, count in rows}

    def errors_by_service(self, context: AnalyticsContext) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for row in self._list_failed_events(context):
            counter[self._service_for_event(row.event_type, row.event_category)] += 1
        return dict(counter.most_common())

    def list_recurring_errors(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[ErrorFrequencyRow], int]:
        counter: Counter[tuple[str, str]] = Counter()
        for row in self._list_failed_events(context):
            reason = ""
            if isinstance(row.event_metadata, dict):
                reason = str(row.event_metadata.get("reason") or "").strip()
            label = reason or row.action or row.event_type
            counter[(label, row.event_category)] += 1

        ranked = [
            ErrorFrequencyRow(label=label, count=count, category=category)
            for (label, category), count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def list_endpoint_failures(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[EndpointFailureRow], int]:
        counter: Counter[tuple[str, str]] = Counter()
        for row in self._list_failed_events(context):
            endpoint = self._endpoint_from_row(row)
            if endpoint is None:
                continue
            service = self._service_for_event(row.event_type, row.event_category)
            counter[(endpoint, service)] += 1

        ranked = [
            EndpointFailureRow(endpoint=endpoint, count=count, service=service)
            for (endpoint, service), count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def list_failed_operations(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[ErrorFrequencyRow], int]:
        counter: Counter[tuple[str, str]] = Counter()
        for row in self._list_failed_events(context):
            label = row.action or row.event_type
            counter[(label, row.event_category)] += 1

        ranked = [
            ErrorFrequencyRow(label=label, count=count, category=category)
            for (label, category), count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def list_retrieval_failure_reasons(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[ErrorFrequencyRow], int]:
        counter: Counter[str] = Counter()
        for metadata in self._fetch_event_metadata(AnalyticsEvents.CHAT_FAILURE, context):
            reason = str(metadata.get("reason") or "Unknown retrieval failure").strip()
            counter[reason or "Unknown retrieval failure"] += 1

        ranked = [
            ErrorFrequencyRow(
                label=reason,
                count=count,
                category=AuditEventCategory.CHAT.value,
            )
            for reason, count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def list_authentication_failure_details(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[ErrorFrequencyRow], int]:
        counter: Counter[str] = Counter()
        for row in self._list_failed_events(context, event_type=AnalyticsEvents.LOGIN_FAILED):
            counter[row.action or AnalyticsEvents.LOGIN_FAILED] += 1

        ranked = [
            ErrorFrequencyRow(
                label=label,
                count=count,
                category=AuditEventCategory.AUTH.value,
            )
            for label, count in counter.most_common()
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def list_upload_failure_details(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[ErrorFrequencyRow], int]:
        query = (
            select(Document)
            .where(Document.status == DocumentStatus.FAILED.value)
            .where(Document.updated_at >= context.start_date)
            .where(Document.updated_at <= context.end_date)
            .order_by(Document.updated_at.desc())
        )
        documents = list(self._db.scalars(query))
        ranked = [
            ErrorFrequencyRow(
                label=document.filename,
                count=1,
                category=AuditEventCategory.DOCUMENT.value,
            )
            for document in documents
        ]
        total = len(ranked)
        return ranked[offset : offset + limit], total

    def _count_failed_events(self, context: AnalyticsContext) -> int:
        query = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.status == AuditStatus.FAILED.value)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
        )
        return self._db.scalar(query) or 0

    def _count_failed_documents(self, context: AnalyticsContext) -> int:
        query = (
            select(func.count())
            .select_from(Document)
            .where(Document.status == DocumentStatus.FAILED.value)
            .where(Document.updated_at >= context.start_date)
            .where(Document.updated_at <= context.end_date)
        )
        return self._db.scalar(query) or 0

    def _count_events(self, event_type: str, context: AnalyticsContext) -> int:
        return self._audit_repository.count(
            filters=AuditSearchFilter(
                event_type=event_type,
                date_from=context.start_date,
                date_to=context.end_date,
            )
        )

    def _list_failed_events(
        self,
        context: AnalyticsContext,
        *,
        event_type: str | None = None,
    ) -> list[AuditLog]:
        query = (
            select(AuditLog)
            .where(AuditLog.status == AuditStatus.FAILED.value)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.desc())
        )
        if event_type is not None:
            query = query.where(AuditLog.event_type == event_type)
        return list(self._db.scalars(query))

    def _list_event_timestamps(
        self,
        context: AnalyticsContext,
        *,
        event_type: str | None = None,
        status: str | None = None,
    ) -> list[datetime]:
        query = (
            select(AuditLog.created_at)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        if event_type is not None:
            query = query.where(AuditLog.event_type == event_type)
        if status is not None:
            query = query.where(AuditLog.status == status)
        return list(self._db.scalars(query))

    def _fetch_event_metadata(
        self,
        event_type: str,
        context: AnalyticsContext,
    ) -> list[dict]:
        query = (
            select(AuditLog.event_metadata)
            .where(AuditLog.event_type == event_type)
            .where(AuditLog.status == AuditStatus.FAILED.value)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
        )
        rows = self._db.scalars(query).all()
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _endpoint_from_row(row: AuditLog) -> str | None:
        if isinstance(row.event_metadata, dict):
            resource = row.event_metadata.get("resource")
            if resource:
                return str(resource)
        if row.resource_type and row.resource_id:
            return f"{row.resource_type}:{row.resource_id}"
        if row.action:
            return row.action
        return None

    @staticmethod
    def _service_for_event(event_type: str, event_category: str) -> str:
        if event_type.startswith("auth."):
            return "authentication"
        if event_type.startswith("security."):
            return "security"
        if event_type.startswith("chat."):
            return "ai_service"
        if event_type.startswith("document."):
            return "documents"
        return event_category.lower()
