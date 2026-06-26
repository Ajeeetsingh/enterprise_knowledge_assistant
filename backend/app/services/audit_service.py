"""Persisted audit logging service (Phase 7.2).

Central entry point for writing audit events to the database.  Structured
log-only audit (Phase 5.6) lives in ``app.audit.service``; this module adds
durable persistence via ``AuditRepository``.

Design principles
---------------
* Constructor-injected ``AuditRepository`` — no global state or singletons.
* ``log_event()`` is failure-safe: never raises to callers.
* Async-first API — ready for future background workers, message queues, and
  SIEM forwarding without changing caller signatures.
* No imports from auth, documents, chat, or authorization modules.

Extension points (not implemented)
--------------------------------
* Replace the direct repository call with an async queue publish.
* Add post-persist hooks for Kafka, RabbitMQ, Datadog, Splunk, or Elastic.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models.audit_log import AuditLog
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository

logger = get_logger(__name__)


def build_audit_service(db: Session) -> AuditService:
    """Construct an ``AuditService`` bound to the given database session."""
    return AuditService(AuditRepository(db))


def run_persisted_audit(
    coro: Coroutine[Any, Any, AuditLog | None],
) -> AuditLog | None:
    """Execute a persisted audit coroutine from synchronous call sites.

    Failure-safe: any unexpected error is logged and ``None`` is returned.
    """
    try:
        return asyncio.run(coro)
    except Exception:
        logger.exception("Unexpected error running persisted audit coroutine")
        return None


class AuditService:
    """Persist audit events through ``AuditRepository``.

    All durable audit logging in the application should eventually pass
    through this service.  Callers must treat a ``None`` return value as a
    non-fatal audit failure and continue their primary operation.
    """

    def __init__(self, audit_repository: AuditRepository) -> None:
        self._audit_repository = audit_repository

    async def log_event(
        self,
        *,
        event_type: str,
        event_category: AuditEventCategory,
        action: str,
        status: AuditStatus,
        user_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog | None:
        """Validate inputs and persist an audit event.

        Returns the persisted ``AuditLog`` on success, or ``None`` when
        validation fails or persistence raises an exception.  This method
        never propagates errors to callers.

        Args:
            event_type: Canonical event identifier (e.g. ``auth.login.success``).
            event_category: High-level domain category for the event.
            action: Human-readable action verb.
            status: Outcome status for the event.
            user_id: Optional UUID of the acting user.
            resource_type: Optional resource class name.
            resource_id: Optional resource identifier.
            metadata: Optional structured context dict.
            ip_address: Optional client IP address.
            user_agent: Optional client user-agent string.

        Returns:
            The persisted ``AuditLog``, or ``None`` on any failure.
        """
        if not self._is_non_empty(event_type):
            logger.warning(
                "Audit event rejected: event_type must not be empty "
                "(category=%s action=%s)",
                event_category,
                action,
            )
            return None

        if not self._is_non_empty(action):
            logger.warning(
                "Audit event rejected: action must not be empty "
                "(event_type=%s category=%s)",
                event_type,
                event_category,
            )
            return None

        try:
            return self._persist_event(
                event_type=event_type,
                event_category=event_category,
                action=action,
                status=status,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception:
            logger.exception(
                "Failed to persist audit event "
                "(event_type=%s category=%s action=%s)",
                event_type,
                event_category,
                action,
            )
            return None

    def _persist_event(
        self,
        *,
        event_type: str,
        event_category: AuditEventCategory,
        action: str,
        status: AuditStatus,
        user_id: uuid.UUID | None,
        resource_type: str | None,
        resource_id: str | None,
        metadata: dict[str, Any] | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> AuditLog:
        """Write the audit record via the repository.

        Separated for future replacement with async queue/worker dispatch.
        """
        return self._audit_repository.create(
            event_type=event_type.strip(),
            event_category=event_category,
            action=action.strip(),
            status=status,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def _is_non_empty(value: str) -> bool:
        """Return ``True`` when *value* contains non-whitespace characters."""
        return bool(value and value.strip())
