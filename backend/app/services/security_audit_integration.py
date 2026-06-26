"""Persisted audit helpers for security and authorization events (Phase 7.5).

JWT tokens, refresh tokens, passwords, and stack traces must never appear
in persisted audit metadata.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.services.audit_service import AuditService, run_persisted_audit


def record_permission_denied(
    audit_service: AuditService,
    *,
    required_permission: str,
    resource: str,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist an authorization denial audit event."""
    metadata: dict[str, Any] = {
        "required_permission": required_permission,
        "resource": resource,
    }
    run_persisted_audit(
        audit_service.log_event(
            event_type="security.permission.denied",
            event_category=AuditEventCategory.SECURITY,
            action="permission_check",
            status=AuditStatus.FAILED,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
    )


def record_invalid_token(
    audit_service: AuditService,
    *,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist a JWT validation failure audit event."""
    run_persisted_audit(
        audit_service.log_event(
            event_type="security.invalid.token",
            event_category=AuditEventCategory.SECURITY,
            action="validate_token",
            status=AuditStatus.FAILED,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"reason": reason},
        )
    )


def record_unauthorized_access(
    audit_service: AuditService,
    *,
    resource: str,
    reason: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Persist an unauthenticated access attempt audit event."""
    run_persisted_audit(
        audit_service.log_event(
            event_type="security.unauthorized.access",
            event_category=AuditEventCategory.SECURITY,
            action="access_protected_resource",
            status=AuditStatus.FAILED,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "resource": resource,
                "reason": reason,
            },
        )
    )
