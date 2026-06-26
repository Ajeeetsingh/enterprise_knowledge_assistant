"""Persisted audit helpers for authentication and user management (Phase 7.3).

All durable auth/user audit events are defined here so endpoints and services
do not duplicate event types, categories, or metadata shapes.

Sensitive data (passwords, hashes, JWT/refresh tokens) must never appear in
metadata or other persisted fields.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.services.audit_service import AuditService, run_persisted_audit


def _username_label(*, email: str, username: str | None = None) -> str:
    """Return the best available non-secret user identifier for metadata."""
    return username or email


def record_login_success(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID,
    email: str,
    username: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a successful login audit event."""
    run_persisted_audit(
        audit_service.log_event(
            event_type="auth.login.success",
            event_category=AuditEventCategory.AUTH,
            action="login",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_type="session",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"username": _username_label(email=email, username=username)},
        )
    )


def record_login_failed(
    audit_service: AuditService,
    *,
    email: str,
    reason: str,
    subject_user_id: uuid.UUID | None = None,
    username: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a failed login audit event."""
    metadata: dict[str, Any] = {
        "username": _username_label(email=email, username=username),
        "reason": reason,
    }
    run_persisted_audit(
        audit_service.log_event(
            event_type="auth.login.failed",
            event_category=AuditEventCategory.AUTH,
            action="login",
            status=AuditStatus.FAILED,
            user_id=subject_user_id,
            resource_type="session",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
    )


def record_logout(
    audit_service: AuditService,
    *,
    user_id: uuid.UUID | None = None,
    email: str | None = None,
    username: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a logout audit event."""
    metadata: dict[str, Any] | None = None
    if email is not None:
        metadata = {"username": _username_label(email=email, username=username)}

    run_persisted_audit(
        audit_service.log_event(
            event_type="auth.logout",
            event_category=AuditEventCategory.AUTH,
            action="logout",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_type="session",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
    )


def record_user_created(
    audit_service: AuditService,
    *,
    admin_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
    target_email: str,
    target_username: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a user-created audit event."""
    run_persisted_audit(
        audit_service.log_event(
            event_type="user.created",
            event_category=AuditEventCategory.ADMIN,
            action="create_user",
            status=AuditStatus.SUCCESS,
            user_id=admin_user_id,
            resource_type="user",
            resource_id=str(target_user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "target_user_id": str(target_user_id),
                "username": _username_label(
                    email=target_email,
                    username=target_username,
                ),
            },
        )
    )


def record_user_disabled(
    audit_service: AuditService,
    *,
    admin_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
    target_email: str,
    target_username: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a user-disabled audit event."""
    run_persisted_audit(
        audit_service.log_event(
            event_type="user.disabled",
            event_category=AuditEventCategory.ADMIN,
            action="disable_user",
            status=AuditStatus.SUCCESS,
            user_id=admin_user_id,
            resource_type="user",
            resource_id=str(target_user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "target_user_id": str(target_user_id),
                "username": _username_label(
                    email=target_email,
                    username=target_username,
                ),
            },
        )
    )
