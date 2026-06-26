"""Unit tests for AuditLog ORM model (Phase 7.1)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from tests.constants import TEST_PASSWORD_HASH
from app.db.models import (
    AuditEventCategory,
    AuditLog,
    AuditStatus,
    Role,
    User,
)
from app.db.repositories.audit_repository import AuditRepository


def _make_user(*, email: str = "audit-user@example.com") -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        username="audituser",
        full_name="Audit User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )


class TestAuditLogCreation:
    def test_create_persists_required_fields(self, db_session: Session) -> None:
        repo = AuditRepository(db_session)
        log = repo.create(
            event_type="auth.login.success",
            event_category=AuditEventCategory.AUTH,
            action="login",
            status=AuditStatus.SUCCESS,
        )

        stored = db_session.get(AuditLog, log.id)
        assert stored is not None
        assert isinstance(stored.id, uuid.UUID)
        assert stored.event_type == "auth.login.success"
        assert stored.action == "login"

    def test_create_sets_created_at(self, db_session: Session) -> None:
        repo = AuditRepository(db_session)
        log = repo.create(
            event_type="system.health.check",
            event_category=AuditEventCategory.SYSTEM,
            action="health_check",
            status=AuditStatus.SUCCESS,
        )
        assert log.created_at is not None


class TestAuditLogEnums:
    def test_event_category_persistence(self, db_session: Session) -> None:
        repo = AuditRepository(db_session)
        log = repo.create(
            event_type="document.read",
            event_category=AuditEventCategory.DOCUMENT,
            action="read",
            status=AuditStatus.SUCCESS,
        )
        assert log.event_category == AuditEventCategory.DOCUMENT
        assert log.event_category_enum is AuditEventCategory.DOCUMENT

    def test_status_persistence(self, db_session: Session) -> None:
        repo = AuditRepository(db_session)
        log = repo.create(
            event_type="auth.login.failure",
            event_category=AuditEventCategory.AUTH,
            action="login",
            status=AuditStatus.FAILED,
        )
        assert log.status == AuditStatus.FAILED
        assert log.status_enum is AuditStatus.FAILED

    def test_all_event_categories_defined(self) -> None:
        values = {category.value for category in AuditEventCategory}
        assert values == {
            "AUTH",
            "DOCUMENT",
            "CHAT",
            "SECURITY",
            "ADMIN",
            "SYSTEM",
        }

    def test_all_statuses_defined(self) -> None:
        values = {status.value for status in AuditStatus}
        assert values == {"SUCCESS", "FAILED", "WARNING"}


class TestAuditLogUserRelationship:
    def test_optional_user_relationship(self, db_session: Session) -> None:
        role = Role(name="Admin", description="Administrator")
        user = _make_user()
        user.roles.append(role)
        db_session.add_all([role, user])
        db_session.commit()

        repo = AuditRepository(db_session)
        log = repo.create(
            event_type="auth.login.success",
            event_category=AuditEventCategory.AUTH,
            action="login",
            status=AuditStatus.SUCCESS,
            user_id=user.id,
        )

        db_session.refresh(log)
        assert log.user is not None
        assert log.user.id == user.id

    def test_system_event_without_user(self, db_session: Session) -> None:
        repo = AuditRepository(db_session)
        log = repo.create(
            event_type="system.startup",
            event_category=AuditEventCategory.SYSTEM,
            action="startup",
            status=AuditStatus.SUCCESS,
        )
        assert log.user_id is None
        assert log.user is None

    def test_audit_survives_user_deletion(self, db_session: Session) -> None:
        role = Role(name="Employee", description="Employee")
        user = _make_user(email="delete-me@example.com")
        user.roles.append(role)
        db_session.add_all([role, user])
        db_session.commit()

        repo = AuditRepository(db_session)
        log = repo.create(
            event_type="auth.logout",
            event_category=AuditEventCategory.AUTH,
            action="logout",
            status=AuditStatus.SUCCESS,
            user_id=user.id,
        )
        log_id = log.id

        db_session.delete(user)
        db_session.commit()

        surviving = db_session.get(AuditLog, log_id)
        assert surviving is not None
        assert surviving.user_id is None


class TestAuditLogMetadataAndContext:
    def test_metadata_json_persistence(self, db_session: Session) -> None:
        repo = AuditRepository(db_session)
        metadata = {"request_id": "abc-123", "attempt": 1}
        log = repo.create(
            event_type="security.access.denied",
            event_category=AuditEventCategory.SECURITY,
            action="access_denied",
            status=AuditStatus.WARNING,
            metadata=metadata,
            ip_address="192.0.2.1",
            user_agent="pytest-agent/1.0",
            resource_type="document",
            resource_id="doc-42",
        )

        db_session.refresh(log)
        assert log.event_metadata == metadata
        assert log.ip_address == "192.0.2.1"
        assert log.user_agent == "pytest-agent/1.0"
        assert log.resource_type == "document"
        assert log.resource_id == "doc-42"


class TestAuditLogTimestamp:
    def test_explicit_created_at_can_be_set(self, db_session: Session) -> None:
        explicit_time = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        log = AuditLog(
            id=uuid.uuid4(),
            event_type="admin.user.created",
            event_category=AuditEventCategory.ADMIN.value,
            action="create_user",
            status=AuditStatus.SUCCESS.value,
            created_at=explicit_time,
        )
        db_session.add(log)
        db_session.commit()

        stored = db_session.get(AuditLog, log.id)
        assert stored is not None
        assert stored.created_at == explicit_time
