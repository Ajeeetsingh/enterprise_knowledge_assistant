"""Read-only system monitoring queries over persisted platform and runtime state.

Aggregates inventory counts, audit outcomes, chat latency samples, and live
database probes. Metrics that are not persisted (API latency, embedding time,
vector index size) are intentionally omitted at the repository layer.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.db.models.audit_log import AuditLog
from app.db.models.conversation import Conversation
from app.db.models.document import Document
from app.db.models.enums.audit import AuditStatus
from app.db.models.message import Message
from app.db.models.user import User
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter
from app.documents.status import DocumentStatus


@dataclass(frozen=True)
class HealthEventRow:
    """Operational health event derived from persisted audit records."""

    timestamp: datetime
    service: str
    status: str
    event_type: str
    detail: str


@dataclass(frozen=True)
class ServiceProbeRow:
    """Current health probe for a platform service."""

    service: str
    status: str
    detail: str


class MonitoringAnalyticsRepository:
    """Persistence and runtime probes for system monitoring dashboards."""

    INACTIVE_DOCUMENT_STATUSES = frozenset(
        {DocumentStatus.DELETED.value, DocumentStatus.FAILED.value}
    )

    def __init__(
        self,
        db: Session,
        *,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        self._db = db
        self._audit_repository = audit_repository or AuditRepository(db)

    def is_database_connected(self) -> bool:
        """Return whether the database accepts a simple probe query."""
        try:
            self._db.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def measure_database_query_time_seconds(self) -> float | None:
        """Return elapsed time for a live ``SELECT 1`` probe, or ``None`` on failure."""
        try:
            start = time.perf_counter()
            self._db.execute(text("SELECT 1"))
            return round(time.perf_counter() - start, 4)
        except Exception:
            return None

    def count_total_users(self) -> int:
        return self._db.scalar(select(func.count()).select_from(User)) or 0

    def count_total_documents(self) -> int:
        query = (
            select(func.count())
            .select_from(Document)
            .where(Document.status != DocumentStatus.DELETED.value)
        )
        return self._db.scalar(query) or 0

    def count_total_conversations(self) -> int:
        return self._db.scalar(select(func.count()).select_from(Conversation)) or 0

    def sum_document_storage_bytes(self) -> int:
        query = (
            select(func.coalesce(func.sum(Document.file_size), 0))
            .select_from(Document)
            .where(Document.status.not_in(tuple(self.INACTIVE_DOCUMENT_STATUSES)))
        )
        return int(self._db.scalar(query) or 0)

    def count_uploaded_files(self) -> int:
        query = (
            select(func.count())
            .select_from(Document)
            .where(Document.status.not_in(tuple(self.INACTIVE_DOCUMENT_STATUSES)))
        )
        return self._db.scalar(query) or 0

    def count_chat_questions(self, context: AnalyticsContext) -> int:
        return self._count_events(AnalyticsEvents.CHAT_QUESTION, context)

    def count_chat_responses(self, context: AnalyticsContext) -> int:
        return self._count_events(AnalyticsEvents.CHAT_RESPONSE, context)

    def count_chat_failures(self, context: AnalyticsContext) -> int:
        return self._count_events(AnalyticsEvents.CHAT_FAILURE, context)

    def count_login_failures(self, context: AnalyticsContext) -> int:
        return self._count_events(AnalyticsEvents.LOGIN_FAILED, context)

    def count_login_successes(self, context: AnalyticsContext) -> int:
        return self._count_events(AnalyticsEvents.LOGIN_SUCCESS, context)

    def count_failed_audit_events(self, context: AnalyticsContext) -> int:
        query = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.status == AuditStatus.FAILED.value)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
        )
        return self._db.scalar(query) or 0

    def list_error_event_timestamps(self, context: AnalyticsContext) -> list[datetime]:
        query = (
            select(AuditLog.created_at)
            .where(AuditLog.status == AuditStatus.FAILED.value)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        return list(self._db.scalars(query))

    def list_health_event_timestamps(self, context: AnalyticsContext) -> list[datetime]:
        query = (
            select(AuditLog.created_at)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        return list(self._db.scalars(query))

    def compute_chat_latency_samples(
        self,
        context: AnalyticsContext,
    ) -> list[tuple[datetime, float]]:
        """Estimate chat turn latency from user-to-assistant message pairs."""
        query = (
            select(Message)
            .where(Message.created_at >= context.start_date)
            .where(Message.created_at <= context.end_date)
            .order_by(Message.conversation_id.asc(), Message.created_at.asc())
        )
        messages = list(self._db.scalars(query))
        samples: list[tuple[datetime, float]] = []
        pending_user_times: dict[uuid.UUID, datetime] = {}

        for message in messages:
            if message.role == "user":
                pending_user_times[message.conversation_id] = message.created_at
                continue
            if message.role != "assistant":
                continue
            user_time = pending_user_times.pop(message.conversation_id, None)
            if user_time is None:
                continue
            delta = (message.created_at - user_time).total_seconds()
            if delta >= 0:
                samples.append((message.created_at, delta))
        return samples

    def list_health_events(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[HealthEventRow], int]:
        """Return recent operational audit events for timeline views."""
        query = (
            select(AuditLog)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.desc())
        )
        rows = list(self._db.scalars(query))
        mapped = [self._map_health_event(row) for row in rows]
        total = len(mapped)
        return mapped[offset : offset + limit], total

    def probe_service_statuses(self, context: AnalyticsContext) -> list[ServiceProbeRow]:
        """Return current service health probes derived from measurable signals."""
        return [
            self._probe_authentication(context),
            self._probe_database(),
            self._probe_ai_service(context),
            self._probe_retrieval_service(context),
            ServiceProbeRow(
                service="background_workers",
                status="unavailable",
                detail="Background workers are not instrumented in this release.",
            ),
        ]

    def _probe_authentication(self, context: AnalyticsContext) -> ServiceProbeRow:
        failures = self.count_login_failures(context)
        successes = self.count_login_successes(context)
        attempts = failures + successes
        if attempts == 0:
            return ServiceProbeRow(
                service="authentication",
                status="healthy",
                detail="No authentication activity recorded in the selected period.",
            )
        failure_rate = failures / attempts
        if failure_rate >= 0.5:
            status = "unavailable"
        elif failure_rate >= 0.2:
            status = "degraded"
        else:
            status = "healthy"
        return ServiceProbeRow(
            service="authentication",
            status=status,
            detail=f"{failures} failed logins of {attempts} attempts",
        )

    def _probe_database(self) -> ServiceProbeRow:
        if self.is_database_connected():
            return ServiceProbeRow(
                service="database",
                status="healthy",
                detail="Database connectivity probe succeeded.",
            )
        return ServiceProbeRow(
            service="database",
            status="unavailable",
            detail="Database connectivity probe failed.",
        )

    def _probe_ai_service(self, context: AnalyticsContext) -> ServiceProbeRow:
        responses = self.count_chat_responses(context)
        failures = self.count_chat_failures(context)
        attempts = responses + failures
        if attempts == 0:
            return ServiceProbeRow(
                service="ai_service",
                status="healthy",
                detail="No AI response activity recorded in the selected period.",
            )
        failure_rate = failures / attempts
        if failure_rate >= 0.5:
            status = "unavailable"
        elif failure_rate >= 0.2:
            status = "degraded"
        else:
            status = "healthy"
        return ServiceProbeRow(
            service="ai_service",
            status=status,
            detail=f"{responses} responses and {failures} failures recorded",
        )

    def _probe_retrieval_service(self, context: AnalyticsContext) -> ServiceProbeRow:
        questions = self.count_chat_questions(context)
        failures = self.count_chat_failures(context)
        if questions == 0:
            return ServiceProbeRow(
                service="retrieval_service",
                status="healthy",
                detail="No retrieval activity recorded in the selected period.",
            )
        failure_rate = failures / questions
        if failure_rate >= 0.5:
            status = "unavailable"
        elif failure_rate >= 0.2:
            status = "degraded"
        else:
            status = "healthy"
        return ServiceProbeRow(
            service="retrieval_service",
            status=status,
            detail=f"{failures} retrieval failures across {questions} questions",
        )

    def _count_events(self, event_type: str, context: AnalyticsContext) -> int:
        return self._audit_repository.count(
            filters=AuditSearchFilter(
                event_type=event_type,
                date_from=context.start_date,
                date_to=context.end_date,
            )
        )

    @staticmethod
    def _map_health_event(row: AuditLog) -> HealthEventRow:
        service = MonitoringAnalyticsRepository._service_for_event(row.event_type)
        status = MonitoringAnalyticsRepository._health_status_for_audit(row.status)
        detail = row.action or row.event_type
        if isinstance(row.event_metadata, dict):
            reason = row.event_metadata.get("reason")
            if reason:
                detail = f"{detail}: {reason}"
        return HealthEventRow(
            timestamp=row.created_at,
            service=service,
            status=status,
            event_type=row.event_type,
            detail=detail,
        )

    @staticmethod
    def _service_for_event(event_type: str) -> str:
        if event_type.startswith("auth."):
            return "authentication"
        if event_type.startswith("chat."):
            return "ai_service"
        if event_type.startswith("document."):
            return "documents"
        if event_type.startswith("security."):
            return "security"
        return "system"

    @staticmethod
    def _health_status_for_audit(status: str) -> str:
        if status == AuditStatus.FAILED.value:
            return "unavailable"
        if status == AuditStatus.WARNING.value:
            return "degraded"
        return "healthy"
