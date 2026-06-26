"""Unit tests for security persisted audit integration (Phase 7.5)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.services import security_audit_integration
from app.services.audit_service import AuditService


def _mock_audit_service() -> MagicMock:
    service = MagicMock(spec=AuditService)
    service.log_event = AsyncMock(return_value=None)
    return service


class TestSecurityPermissionDeniedAudit:
    def test_permission_denied_event(self) -> None:
        mock_audit_service = _mock_audit_service()
        user_id = uuid.uuid4()

        security_audit_integration.record_permission_denied(
            mock_audit_service,
            user_id=user_id,
            required_permission="permission:document:read",
            resource="/api/v1/documents",
            ip_address="10.0.0.1",
            user_agent="pytest/1.0",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "security.permission.denied"
        assert kwargs["event_category"] is AuditEventCategory.SECURITY
        assert kwargs["status"] is AuditStatus.FAILED
        assert kwargs["user_id"] == user_id
        assert kwargs["metadata"] == {
            "required_permission": "permission:document:read",
            "resource": "/api/v1/documents",
        }


class TestSecurityInvalidTokenAudit:
    def test_invalid_token_event(self) -> None:
        mock_audit_service = _mock_audit_service()

        security_audit_integration.record_invalid_token(
            mock_audit_service,
            reason="expired token",
            ip_address="192.0.2.5",
            user_agent="AuthClient/2.0",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "security.invalid.token"
        assert kwargs["event_category"] is AuditEventCategory.SECURITY
        assert kwargs["status"] is AuditStatus.FAILED
        assert kwargs.get("user_id") is None
        assert kwargs["metadata"] == {"reason": "expired token"}


class TestSecurityUnauthorizedAccessAudit:
    def test_unauthorized_access_event(self) -> None:
        mock_audit_service = _mock_audit_service()

        security_audit_integration.record_unauthorized_access(
            mock_audit_service,
            resource="/api/v1/chat/ask",
            reason="missing token",
            ip_address="127.0.0.1",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "security.unauthorized.access"
        assert kwargs["event_category"] is AuditEventCategory.SECURITY
        assert kwargs["status"] is AuditStatus.FAILED
        assert kwargs["metadata"] == {
            "resource": "/api/v1/chat/ask",
            "reason": "missing token",
        }


class TestSecurityAuditFailureNonFatal:
    def test_repository_failure_does_not_raise(self) -> None:
        repository = MagicMock()
        repository.create.side_effect = RuntimeError("database down")
        service = AuditService(repository)

        security_audit_integration.record_invalid_token(
            service,
            reason="invalid signature",
        )

    @patch(
        "app.services.security_audit_integration.run_persisted_audit",
        return_value=None,
    )
    def test_record_helpers_do_not_raise_when_persisted_audit_returns_none(
        self,
        _mock_run_persisted: MagicMock,
    ) -> None:
        mock_audit_service = _mock_audit_service()
        user_id = uuid.uuid4()

        security_audit_integration.record_permission_denied(
            mock_audit_service,
            user_id=user_id,
            required_permission="role:Admin",
            resource="/api/v1/auth/admin-demo",
        )
        security_audit_integration.record_invalid_token(
            mock_audit_service,
            reason="malformed token",
        )
        security_audit_integration.record_unauthorized_access(
            mock_audit_service,
            resource="/api/v1/auth/me",
            reason="missing token",
        )
