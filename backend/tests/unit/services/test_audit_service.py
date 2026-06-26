"""Unit tests for persisted AuditService (Phase 7.2)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.db.models.audit_log import AuditLog
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService


@pytest.fixture
def mock_repo() -> MagicMock:
    return MagicMock(spec=AuditRepository)


@pytest.fixture
def audit_service(mock_repo: MagicMock) -> AuditService:
    return AuditService(audit_repository=mock_repo)


def _sample_audit_log(**overrides: object) -> AuditLog:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "event_type": "auth.login.success",
        "event_category": AuditEventCategory.AUTH.value,
        "user_id": uuid.uuid4(),
        "resource_type": None,
        "resource_id": None,
        "action": "login",
        "status": AuditStatus.SUCCESS.value,
        "event_metadata": None,
        "ip_address": None,
        "user_agent": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return AuditLog(**defaults)


def _log_event(
    service: AuditService,
    **kwargs: object,
) -> AuditLog | None:
    defaults: dict[str, object] = {
        "event_type": "auth.login.success",
        "event_category": AuditEventCategory.AUTH,
        "action": "login",
        "status": AuditStatus.SUCCESS,
    }
    defaults.update(kwargs)
    return asyncio.run(service.log_event(**defaults))  # type: ignore[arg-type]


class TestAuditServiceLogEventSuccess:
    def test_successful_event_logging(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        expected = _sample_audit_log(user_id=user_id)
        mock_repo.create.return_value = expected

        result = _log_event(audit_service, user_id=user_id)

        assert result is expected
        mock_repo.create.assert_called_once_with(
            event_type="auth.login.success",
            event_category=AuditEventCategory.AUTH,
            action="login",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_type=None,
            resource_id=None,
            metadata=None,
            ip_address=None,
            user_agent=None,
        )

    def test_returns_persisted_audit_log(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        persisted = _sample_audit_log(event_type="document.read")
        mock_repo.create.return_value = persisted

        result = _log_event(
            audit_service,
            event_type="document.read",
            event_category=AuditEventCategory.DOCUMENT,
            action="read",
            status=AuditStatus.SUCCESS,
        )

        assert result is not None
        assert result.event_type == "document.read"
        assert isinstance(result.id, uuid.UUID)


class TestAuditServiceLogEventFailures:
    def test_repository_exception_returns_none(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        mock_repo.create.side_effect = RuntimeError("database unavailable")

        result = _log_event(audit_service)

        assert result is None

    def test_invalid_event_type_returns_none(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        result = _log_event(audit_service, event_type="")

        assert result is None
        mock_repo.create.assert_not_called()

    def test_whitespace_event_type_returns_none(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        result = _log_event(audit_service, event_type="   ")

        assert result is None
        mock_repo.create.assert_not_called()

    def test_invalid_action_returns_none(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        result = _log_event(audit_service, action="")

        assert result is None
        mock_repo.create.assert_not_called()

    def test_whitespace_action_returns_none(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        result = _log_event(audit_service, action="\t\n")

        assert result is None
        mock_repo.create.assert_not_called()


class TestAuditServiceLogEventOptionalFields:
    def test_metadata_persisted_correctly(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        metadata = {"request_id": "req-123", "attempt": 2}
        mock_repo.create.return_value = _sample_audit_log(event_metadata=metadata)

        _log_event(
            audit_service,
            metadata=metadata,
            status=AuditStatus.WARNING,
            event_category=AuditEventCategory.SECURITY,
            event_type="security.access.denied",
            action="access_denied",
        )

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args.kwargs
        assert call_kwargs["metadata"] == metadata

    def test_optional_fields_accepted(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        mock_repo.create.return_value = _sample_audit_log(user_id=user_id)

        _log_event(
            audit_service,
            user_id=user_id,
            resource_type="document",
            resource_id="doc-99",
            ip_address="192.0.2.1",
            user_agent="pytest/1.0",
        )

        mock_repo.create.assert_called_once_with(
            event_type="auth.login.success",
            event_category=AuditEventCategory.AUTH,
            action="login",
            status=AuditStatus.SUCCESS,
            user_id=user_id,
            resource_type="document",
            resource_id="doc-99",
            metadata=None,
            ip_address="192.0.2.1",
            user_agent="pytest/1.0",
        )


class TestAuditServiceNeverRaises:
    def test_service_never_raises_on_repository_failure(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        mock_repo.create.side_effect = Exception("unexpected")

        result = _log_event(audit_service)

        assert result is None

    def test_service_never_raises_on_validation_failure(
        self,
        audit_service: AuditService,
    ) -> None:
        result = _log_event(audit_service, event_type="", action="")

        assert result is None

    @patch.object(AuditService, "_persist_event", side_effect=ValueError("boom"))
    def test_service_never_raises_on_unexpected_internal_error(
        self,
        _mock_persist: MagicMock,
        audit_service: AuditService,
    ) -> None:
        result = _log_event(audit_service)

        assert result is None

    def test_strips_event_type_and_action_before_persist(
        self,
        audit_service: AuditService,
        mock_repo: MagicMock,
    ) -> None:
        mock_repo.create.return_value = _sample_audit_log()

        _log_event(
            audit_service,
            event_type="  auth.login.success  ",
            action="  login  ",
        )

        mock_repo.create.assert_called_once()
        call_kwargs = mock_repo.create.call_args.kwargs
        assert call_kwargs["event_type"] == "auth.login.success"
        assert call_kwargs["action"] == "login"
