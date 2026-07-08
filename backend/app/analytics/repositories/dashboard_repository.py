"""Read-only dashboard queries over persisted platform data.

Aggregates from source-of-truth tables only (``AuditLog``, ``User``,
``Conversation``, ``Document``). Future phases may introduce pre-aggregated
metric tables or scheduled rollups if query volume requires it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.db.models.audit_log import AuditLog
from app.db.models.user import User
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.document_repository import DocumentRepository


@dataclass(frozen=True)
class ChatAnalyticsSnapshot:
    """Aggregated chat activity for a reporting window."""

    questions_asked: int
    answers_generated: int
    retrieval_failures: int
    average_confidence_score: float | None
    average_citation_count: float | None


class DashboardRepository:
    """Persistence queries for dashboard aggregation.

    Contains read-only SQL; business interpretation belongs in services.
    """

    def __init__(
        self,
        db: Session,
        *,
        audit_repository: AuditRepository | None = None,
        document_repository: DocumentRepository | None = None,
        conversation_repository: ConversationRepository | None = None,
    ) -> None:
        self._db = db
        self._audit_repository = audit_repository or AuditRepository(db)
        self._document_repository = document_repository or DocumentRepository(db)
        self._conversation_repository = conversation_repository or ConversationRepository(db)

    def count_users(self, *, active_only: bool = False) -> int:
        """Return total or active user count."""
        query = select(func.count()).select_from(User)
        if active_only:
            query = query.where(User.is_active.is_(True))
        return self._db.scalar(query) or 0

    def count_distinct_active_users(self, context: AnalyticsContext) -> int:
        """Return users with at least one audit event in *context*."""
        query = (
            select(func.count(func.distinct(AuditLog.user_id)))
            .select_from(AuditLog)
            .where(AuditLog.user_id.is_not(None))
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
        )
        return self._db.scalar(query) or 0

    def count_audit_events(
        self,
        *,
        event_type: str | None = None,
        context: AnalyticsContext | None = None,
    ) -> int:
        """Return audit event count with optional filters."""
        filters = self._to_audit_filter(event_type=event_type, context=context)
        return self._audit_repository.count(filters=filters)

    def count_documents(self) -> int:
        """Return total persisted documents."""
        return self._document_repository.count()

    def count_conversations(self) -> int:
        """Return total persisted conversations."""
        return self._conversation_repository.count()

    def get_chat_snapshot(self, context: AnalyticsContext) -> ChatAnalyticsSnapshot:
        """Aggregate chat-related audit metrics for *context*."""
        answer_logs = self._fetch_event_metadata(
            event_type=AnalyticsEvents.CHAT_RESPONSE,
            context=context,
        )
        confidence_values = [
            float(row["confidence_score"])
            for row in answer_logs
            if row.get("confidence_score") is not None
            and isinstance(row["confidence_score"], (int, float))
        ]
        citation_values = [
            float(row["citation_count"])
            for row in answer_logs
            if row.get("citation_count") is not None
            and isinstance(row["citation_count"], (int, float))
        ]

        return ChatAnalyticsSnapshot(
            questions_asked=self.count_audit_events(
                event_type=AnalyticsEvents.CHAT_QUESTION,
                context=context,
            ),
            answers_generated=len(answer_logs),
            retrieval_failures=self.count_audit_events(
                event_type=AnalyticsEvents.CHAT_FAILURE,
                context=context,
            ),
            average_confidence_score=(
                sum(confidence_values) / len(confidence_values)
                if confidence_values
                else None
            ),
            average_citation_count=(
                sum(citation_values) / len(citation_values) if citation_values else None
            ),
        )

    def list_event_timestamps(
        self,
        *,
        event_type: str,
        context: AnalyticsContext,
    ) -> list[datetime]:
        """Return ``created_at`` timestamps for matching audit events."""
        query = (
            select(AuditLog.created_at)
            .where(AuditLog.event_type == event_type)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        return list(self._db.scalars(query))

    def _fetch_event_metadata(
        self,
        *,
        event_type: str,
        context: AnalyticsContext,
    ) -> list[dict]:
        query = (
            select(AuditLog.event_metadata)
            .where(AuditLog.event_type == event_type)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
        )
        rows = self._db.scalars(query).all()
        return [row for row in rows if isinstance(row, dict)]

    @staticmethod
    def _to_audit_filter(
        *,
        event_type: str | None,
        context: AnalyticsContext | None,
    ) -> AuditSearchFilter | None:
        if event_type is None and context is None:
            return None
        return AuditSearchFilter(
            event_type=event_type,
            date_from=context.start_date if context else None,
            date_to=context.end_date if context else None,
        )
