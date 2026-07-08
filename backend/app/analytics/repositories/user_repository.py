"""Read-only user analytics queries over persisted platform data.

Aggregates from ``User``, ``Conversation``, and ``AuditLog`` only. Future
phases may introduce pre-aggregated metric tables if query volume requires it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.analytics.context import AnalyticsContext
from app.db.models.audit_log import AuditLog
from app.db.models.conversation import Conversation
from app.db.models.user import User
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter


@dataclass(frozen=True)
class UserActivityRow:
    """Per-user activity metrics for engagement tables."""

    user_id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    conversation_count: int
    question_count: int
    last_active_at: datetime | None


class UserRepository:
    """Persistence queries for user analytics aggregation."""

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

    def count_total_users(self) -> int:
        """Return total registered users."""
        return self._db.scalar(select(func.count()).select_from(User)) or 0

    def count_active_accounts(self) -> int:
        """Return users with ``is_active=True``."""
        query = select(func.count()).select_from(User).where(User.is_active.is_(True))
        return self._db.scalar(query) or 0

    def count_new_users(self, context: AnalyticsContext) -> int:
        """Return users registered within *context*."""
        query = (
            select(func.count())
            .select_from(User)
            .where(User.created_at >= context.start_date)
            .where(User.created_at <= context.end_date)
        )
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

    def count_conversations(self, context: AnalyticsContext) -> int:
        """Return conversations created within *context*."""
        query = (
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.created_at >= context.start_date)
            .where(Conversation.created_at <= context.end_date)
        )
        return self._db.scalar(query) or 0

    def count_questions(self, context: AnalyticsContext) -> int:
        """Return chat questions asked within *context*."""
        return self._audit_repository.count(
            filters=AuditSearchFilter(
                event_type=AnalyticsEvents.CHAT_QUESTION,
                date_from=context.start_date,
                date_to=context.end_date,
            )
        )

    def count_distinct_question_askers(self, context: AnalyticsContext) -> int:
        """Return distinct users who asked questions in *context*."""
        query = (
            select(func.count(func.distinct(AuditLog.user_id)))
            .select_from(AuditLog)
            .where(AuditLog.event_type == AnalyticsEvents.CHAT_QUESTION)
            .where(AuditLog.user_id.is_not(None))
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
        )
        return self._db.scalar(query) or 0

    def list_user_registration_timestamps(
        self,
        context: AnalyticsContext,
    ) -> list[datetime]:
        """Return registration timestamps within *context*."""
        query = (
            select(User.created_at)
            .where(User.created_at >= context.start_date)
            .where(User.created_at <= context.end_date)
            .order_by(User.created_at.asc())
        )
        return list(self._db.scalars(query))

    def list_active_user_timestamps(self, context: AnalyticsContext) -> list[datetime]:
        """Return audit timestamps for any user activity in *context*."""
        query = (
            select(AuditLog.created_at)
            .where(AuditLog.user_id.is_not(None))
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        return list(self._db.scalars(query))

    def list_event_timestamps(
        self,
        event_type: str,
        context: AnalyticsContext,
    ) -> list[datetime]:
        """Return audit timestamps for *event_type* within *context*."""
        query = (
            select(AuditLog.created_at)
            .where(AuditLog.event_type == event_type)
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .order_by(AuditLog.created_at.asc())
        )
        return list(self._db.scalars(query))

    def list_conversation_timestamps(self, context: AnalyticsContext) -> list[datetime]:
        """Return conversation creation timestamps within *context*."""
        query = (
            select(Conversation.created_at)
            .where(Conversation.created_at >= context.start_date)
            .where(Conversation.created_at <= context.end_date)
            .order_by(Conversation.created_at.asc())
        )
        return list(self._db.scalars(query))

    def list_top_active_users(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[UserActivityRow], int]:
        """Return users ranked by question count in *context*."""
        question_counts = (
            select(
                AuditLog.user_id.label("user_id"),
                func.count().label("question_count"),
                func.max(AuditLog.created_at).label("last_active_at"),
            )
            .where(AuditLog.event_type == AnalyticsEvents.CHAT_QUESTION)
            .where(AuditLog.user_id.is_not(None))
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .group_by(AuditLog.user_id)
            .subquery()
        )
        conversation_counts = (
            select(
                Conversation.user_id.label("user_id"),
                func.count().label("conversation_count"),
            )
            .where(Conversation.created_at >= context.start_date)
            .where(Conversation.created_at <= context.end_date)
            .group_by(Conversation.user_id)
            .subquery()
        )

        total_query = select(func.count()).select_from(question_counts)
        total = self._db.scalar(total_query) or 0

        query = (
            select(
                User.id,
                User.email,
                User.full_name,
                User.is_active,
                func.coalesce(conversation_counts.c.conversation_count, 0),
                question_counts.c.question_count,
                question_counts.c.last_active_at,
            )
            .join(question_counts, User.id == question_counts.c.user_id)
            .outerjoin(
                conversation_counts,
                User.id == conversation_counts.c.user_id,
            )
            .order_by(question_counts.c.question_count.desc(), User.email.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = self._db.execute(query).all()
        items = [
            UserActivityRow(
                user_id=row[0],
                email=row[1],
                full_name=row[2],
                is_active=row[3],
                conversation_count=int(row[4]),
                question_count=int(row[5]),
                last_active_at=row[6],
            )
            for row in rows
        ]
        return items, total

    def list_least_active_users(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[UserActivityRow], int]:
        """Return users ranked by fewest questions in *context*."""
        question_counts = (
            select(
                AuditLog.user_id.label("user_id"),
                func.count().label("question_count"),
                func.max(AuditLog.created_at).label("last_active_at"),
            )
            .where(AuditLog.event_type == AnalyticsEvents.CHAT_QUESTION)
            .where(AuditLog.user_id.is_not(None))
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .group_by(AuditLog.user_id)
            .subquery()
        )
        conversation_counts = (
            select(
                Conversation.user_id.label("user_id"),
                func.count().label("conversation_count"),
            )
            .where(Conversation.created_at >= context.start_date)
            .where(Conversation.created_at <= context.end_date)
            .group_by(Conversation.user_id)
            .subquery()
        )

        total = self._db.scalar(select(func.count()).select_from(question_counts)) or 0

        query = (
            select(
                User.id,
                User.email,
                User.full_name,
                User.is_active,
                func.coalesce(conversation_counts.c.conversation_count, 0),
                question_counts.c.question_count,
                question_counts.c.last_active_at,
            )
            .join(question_counts, User.id == question_counts.c.user_id)
            .outerjoin(
                conversation_counts,
                User.id == conversation_counts.c.user_id,
            )
            .order_by(question_counts.c.question_count.asc(), User.email.asc())
            .offset(offset)
            .limit(limit)
        )
        rows = self._db.execute(query).all()
        items = [
            UserActivityRow(
                user_id=row[0],
                email=row[1],
                full_name=row[2],
                is_active=row[3],
                conversation_count=int(row[4]),
                question_count=int(row[5]),
                last_active_at=row[6],
            )
            for row in rows
        ]
        return items, total

    def list_inactive_users(
        self,
        context: AnalyticsContext,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[list[UserActivityRow], int]:
        """Return active accounts with no audit activity in *context*."""
        active_user_ids = (
            select(AuditLog.user_id)
            .where(AuditLog.user_id.is_not(None))
            .where(AuditLog.created_at >= context.start_date)
            .where(AuditLog.created_at <= context.end_date)
            .distinct()
        )
        count_query = (
            select(func.count())
            .select_from(User)
            .where(User.is_active.is_(True))
            .where(User.id.not_in(active_user_ids))
        )
        total = self._db.scalar(count_query) or 0

        query = (
            select(User)
            .where(User.is_active.is_(True))
            .where(User.id.not_in(active_user_ids))
            .order_by(User.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        users = list(self._db.scalars(query))
        items = [
            UserActivityRow(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                conversation_count=0,
                question_count=0,
                last_active_at=None,
            )
            for user in users
        ]
        return items, total
