"""Audit log repository — persistence only, no business logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.models.enums.audit import AuditEventCategory, AuditStatus


@dataclass(frozen=True)
class AuditSearchFilter:
    """Optional filters for audit log search."""

    event_type: str | None = None
    event_category: AuditEventCategory | str | None = None
    status: AuditStatus | str | None = None
    user_id: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class AuditRepository:
    """CRUD operations for ``AuditLog`` records.

    This repository contains *only* persistence logic.  Event emission,
    authorization, and domain-specific audit wiring belong in later phases.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Write operations                                                     #
    # ------------------------------------------------------------------ #

    def create(
        self,
        *,
        event_type: str,
        event_category: AuditEventCategory | str,
        action: str,
        status: AuditStatus | str,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Persist a new audit log record and return the created row.

        Args:
            event_type: Canonical event identifier string.
            event_category: Domain category (enum member or stored value).
            action: Human-readable action verb for the event.
            status: Outcome status (enum member or stored value).
            user_id: Optional UUID of the acting user.
            resource_type: Optional resource class (e.g. ``document``).
            resource_id: Optional resource identifier string.
            metadata: Optional structured context dict.
            ip_address: Optional client IP address.
            user_agent: Optional client user-agent string.

        Returns:
            The newly persisted ``AuditLog`` instance.
        """
        category_value = (
            event_category.value
            if isinstance(event_category, AuditEventCategory)
            else str(event_category)
        )
        status_value = (
            status.value if isinstance(status, AuditStatus) else str(status)
        )
        audit_log = AuditLog(
            id=uuid.uuid4(),
            event_type=event_type,
            event_category=category_value,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status_value,
            event_metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._db.add(audit_log)
        self._db.commit()
        self._db.refresh(audit_log)
        return audit_log

    # ------------------------------------------------------------------ #
    # Read operations                                                      #
    # ------------------------------------------------------------------ #

    def get_by_id(self, audit_log_id: uuid.UUID) -> AuditLog | None:
        """Return an audit log by primary key, or ``None`` if not found."""
        return self._db.get(AuditLog, audit_log_id)

    def list_paginated(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Return a page of audit logs ordered newest-first.

        Args:
            limit: Maximum number of records to return.
            offset: Number of records to skip (for pagination).

        Returns:
            A 2-tuple of ``(audit_logs, total_count)`` where *total_count*
            reflects all matching records before pagination.
        """
        base_query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)

        total: int = self._db.scalar(count_query) or 0
        audit_logs = list(
            self._db.scalars(
                base_query
                .order_by(AuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return audit_logs, total

    def search(
        self,
        *,
        filters: AuditSearchFilter | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Return a filtered page of audit logs ordered newest-first.

        Args:
            filters: Optional search filters.  ``None`` returns all records.
            limit: Maximum number of records to return.
            offset: Number of records to skip (for pagination).

        Returns:
            A 2-tuple of ``(audit_logs, total_count)`` where *total_count*
            reflects all matching records before pagination.
        """
        query = select(AuditLog)
        count_query = select(func.count()).select_from(AuditLog)

        if filters is not None:
            if filters.event_type is not None:
                query = query.where(AuditLog.event_type == filters.event_type)
                count_query = count_query.where(
                    AuditLog.event_type == filters.event_type
                )
            if filters.event_category is not None:
                category_value = (
                    filters.event_category.value
                    if isinstance(filters.event_category, AuditEventCategory)
                    else str(filters.event_category)
                )
                query = query.where(AuditLog.event_category == category_value)
                count_query = count_query.where(
                    AuditLog.event_category == category_value
                )
            if filters.status is not None:
                status_value = (
                    filters.status.value
                    if isinstance(filters.status, AuditStatus)
                    else str(filters.status)
                )
                query = query.where(AuditLog.status == status_value)
                count_query = count_query.where(AuditLog.status == status_value)
            if filters.user_id is not None:
                query = query.where(AuditLog.user_id == filters.user_id)
                count_query = count_query.where(
                    AuditLog.user_id == filters.user_id
                )
            if filters.date_from is not None:
                query = query.where(AuditLog.created_at >= filters.date_from)
                count_query = count_query.where(
                    AuditLog.created_at >= filters.date_from
                )
            if filters.date_to is not None:
                query = query.where(AuditLog.created_at <= filters.date_to)
                count_query = count_query.where(
                    AuditLog.created_at <= filters.date_to
                )

        total: int = self._db.scalar(count_query) or 0
        audit_logs = list(
            self._db.scalars(
                query
                .order_by(AuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return audit_logs, total

    def count(self, *, filters: AuditSearchFilter | None = None) -> int:
        """Return the number of audit logs matching optional filters."""
        count_query = select(func.count()).select_from(AuditLog)

        if filters is not None:
            if filters.event_type is not None:
                count_query = count_query.where(
                    AuditLog.event_type == filters.event_type
                )
            if filters.event_category is not None:
                category_value = (
                    filters.event_category.value
                    if isinstance(filters.event_category, AuditEventCategory)
                    else str(filters.event_category)
                )
                count_query = count_query.where(
                    AuditLog.event_category == category_value
                )
            if filters.status is not None:
                status_value = (
                    filters.status.value
                    if isinstance(filters.status, AuditStatus)
                    else str(filters.status)
                )
                count_query = count_query.where(AuditLog.status == status_value)
            if filters.user_id is not None:
                count_query = count_query.where(
                    AuditLog.user_id == filters.user_id
                )
            if filters.date_from is not None:
                count_query = count_query.where(
                    AuditLog.created_at >= filters.date_from
                )
            if filters.date_to is not None:
                count_query = count_query.where(
                    AuditLog.created_at <= filters.date_to
                )

        return self._db.scalar(count_query) or 0
