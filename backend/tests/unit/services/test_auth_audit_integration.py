"""Unit tests for authentication and user-management persisted audit integration."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.services import auth_audit_integration, auth_service
from app.services.audit_service import AuditService


@pytest.fixture
def mock_audit_service() -> MagicMock:
    service = MagicMock(spec=AuditService)
    service.log_event = AsyncMock(return_value=None)
    return service


class TestLoginSuccessAudit:
    def test_login_success_audit_event(self, mock_audit_service: MagicMock) -> None:
        user_id = uuid.uuid4()

        auth_audit_integration.record_login_success(
            mock_audit_service,
            user_id=user_id,
            email="user@example.com",
            username="testuser",
            ip_address="192.0.2.1",
            user_agent="pytest/1.0",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "auth.login.success"
        assert kwargs["event_category"] is AuditEventCategory.AUTH
        assert kwargs["action"] == "login"
        assert kwargs["status"] is AuditStatus.SUCCESS
        assert kwargs["user_id"] == user_id
        assert kwargs["metadata"] == {"username": "testuser"}
        assert kwargs["ip_address"] == "192.0.2.1"
        assert kwargs["user_agent"] == "pytest/1.0"


class TestLoginFailureAudit:
    def test_login_failure_audit_event(self, mock_audit_service: MagicMock) -> None:
        subject_user_id = uuid.uuid4()

        auth_audit_integration.record_login_failed(
            mock_audit_service,
            email="user@example.com",
            reason="Invalid email or password.",
            subject_user_id=subject_user_id,
            ip_address="10.0.0.5",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "auth.login.failed"
        assert kwargs["event_category"] is AuditEventCategory.AUTH
        assert kwargs["status"] is AuditStatus.FAILED
        assert kwargs["user_id"] == subject_user_id
        assert kwargs["metadata"] == {
            "username": "user@example.com",
            "reason": "Invalid email or password.",
        }


class TestLogoutAudit:
    def test_logout_audit_event(self, mock_audit_service: MagicMock) -> None:
        auth_audit_integration.record_logout(
            mock_audit_service,
            ip_address="192.0.2.10",
            user_agent="LogoutAgent/1.0",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "auth.logout"
        assert kwargs["event_category"] is AuditEventCategory.AUTH
        assert kwargs["status"] is AuditStatus.SUCCESS
        assert kwargs["user_id"] is None
        assert kwargs["metadata"] is None


class TestUserCreatedAudit:
    def test_user_created_audit_event(self, mock_audit_service: MagicMock) -> None:
        admin_id = uuid.uuid4()
        target_id = uuid.uuid4()

        auth_audit_integration.record_user_created(
            mock_audit_service,
            admin_user_id=admin_id,
            target_user_id=target_id,
            target_email="new@example.com",
            target_username="newuser",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "user.created"
        assert kwargs["event_category"] is AuditEventCategory.ADMIN
        assert kwargs["status"] is AuditStatus.SUCCESS
        assert kwargs["user_id"] == admin_id
        assert kwargs["resource_type"] == "user"
        assert kwargs["resource_id"] == str(target_id)
        assert kwargs["metadata"] == {
            "target_user_id": str(target_id),
            "username": "newuser",
        }


class TestUserDisabledAudit:
    def test_user_disabled_audit_event(self, mock_audit_service: MagicMock) -> None:
        admin_id = uuid.uuid4()
        target_id = uuid.uuid4()

        auth_audit_integration.record_user_disabled(
            mock_audit_service,
            admin_user_id=admin_id,
            target_user_id=target_id,
            target_email="disabled@example.com",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "user.disabled"
        assert kwargs["event_category"] is AuditEventCategory.ADMIN
        assert kwargs["action"] == "disable_user"
        assert kwargs["status"] is AuditStatus.SUCCESS
        assert kwargs["user_id"] == admin_id
        assert kwargs["resource_id"] == str(target_id)


class TestAuditFailureDoesNotBreakAuthFlow:
    def test_repository_failure_does_not_raise_from_record_helper(self) -> None:
        repository = MagicMock()
        repository.create.side_effect = RuntimeError("database down")
        service = AuditService(repository)

        auth_audit_integration.record_login_success(
            service,
            user_id=uuid.uuid4(),
            email="user@example.com",
        )

    @patch("app.services.auth_audit_integration.run_persisted_audit", return_value=None)
    def test_record_helpers_do_not_raise_when_persisted_audit_returns_none(
        self,
        _mock_run_persisted: MagicMock,
        mock_audit_service: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        target_id = uuid.uuid4()

        auth_audit_integration.record_login_success(
            mock_audit_service,
            user_id=user_id,
            email="user@example.com",
        )
        auth_audit_integration.record_login_failed(
            mock_audit_service,
            email="user@example.com",
            reason="Invalid email or password.",
        )
        auth_audit_integration.record_logout(mock_audit_service)
        auth_audit_integration.record_user_created(
            mock_audit_service,
            admin_user_id=admin_id,
            target_user_id=target_id,
            target_email="new@example.com",
        )
        auth_audit_integration.record_user_disabled(
            mock_audit_service,
            admin_user_id=admin_id,
            target_user_id=target_id,
            target_email="disabled@example.com",
        )

    def test_inactive_account_error_exposes_subject_user_id(self) -> None:
        subject_user_id = uuid.uuid4()
        error = auth_service.InactiveAccountError(subject_user_id=subject_user_id)

        assert error.subject_user_id == subject_user_id
        assert error.status_code == 403

