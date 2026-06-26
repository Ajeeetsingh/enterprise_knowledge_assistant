"""Operational monitoring summaries for administrators (Phase 7.7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.document_repository import DocumentRepository


@dataclass(frozen=True)
class MonitoringSummary:
    """Aggregated business metrics for operational dashboards."""

    total_users: int
    active_users: int
    total_documents: int
    total_conversations: int
    questions_today: int
    failed_logins_today: int
    audit_events_today: int


def _utc_start_of_today() -> datetime:
    """Return midnight UTC for the current calendar day."""
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class MonitoringService:
    """Aggregate lightweight business metrics from persisted data."""

    def __init__(
        self,
        db: Session,
        audit_repository: AuditRepository,
        document_repository: DocumentRepository,
        conversation_repository: ConversationRepository,
    ) -> None:
        self._db = db
        self._audit_repository = audit_repository
        self._document_repository = document_repository
        self._conversation_repository = conversation_repository

    def get_summary(self) -> MonitoringSummary:
        """Return a snapshot of platform activity and inventory counts."""
        start_of_day = _utc_start_of_today()
        today_filter = AuditSearchFilter(date_from=start_of_day)

        return MonitoringSummary(
            total_users=self._count_users(active_only=False),
            active_users=self._count_users(active_only=True),
            total_documents=self._document_repository.count(),
            total_conversations=self._conversation_repository.count(),
            questions_today=self._audit_repository.count(
                filters=AuditSearchFilter(
                    event_type="chat.question.asked",
                    date_from=start_of_day,
                )
            ),
            failed_logins_today=self._audit_repository.count(
                filters=AuditSearchFilter(
                    event_type="auth.login.failed",
                    date_from=start_of_day,
                )
            ),
            audit_events_today=self._audit_repository.count(filters=today_filter),
        )

    def _count_users(self, *, active_only: bool) -> int:
        query = select(func.count()).select_from(User)
        if active_only:
            query = query.where(User.is_active.is_(True))
        return self._db.scalar(query) or 0


def build_monitoring_service(db: Session) -> MonitoringService:
    """Construct a monitoring service bound to the given database session."""
    return MonitoringService(
        db=db,
        audit_repository=AuditRepository(db),
        document_repository=DocumentRepository(db),
        conversation_repository=ConversationRepository(db),
    )
