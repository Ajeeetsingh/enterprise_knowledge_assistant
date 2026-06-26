"""Unit tests for MonitoringService (Phase 7.7)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.db.base import Base
from app.db.models import AuditLog, Conversation, Document, Role, User  # noqa: F401
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter
from app.services.monitoring_service import MonitoringService, _utc_start_of_today


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_get_summary_counts_users_and_audit_events(db_session: Session) -> None:
    active_user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    inactive_user = User(
        email="inactive@example.com",
        username="inactive",
        full_name="Inactive User",
        password_hash=hash_password("secret"),
        is_active=False,
    )
    db_session.add_all([active_user, inactive_user])
    db_session.commit()

    audit_repo = AuditRepository(db_session)
    start_of_day = _utc_start_of_today()
    audit_repo.create(
        event_type="chat.question.asked",
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=active_user.id,
    )
    audit_repo.create(
        event_type="auth.login.failed",
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.FAILED,
    )
    audit_repo.create(
        event_type="auth.login.success",
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.SUCCESS,
        user_id=active_user.id,
    )

    document_repo = MagicMock()
    document_repo.count.return_value = 4
    conversation_repo = MagicMock()
    conversation_repo.count.return_value = 2

    service = MonitoringService(
        db=db_session,
        audit_repository=audit_repo,
        document_repository=document_repo,
        conversation_repository=conversation_repo,
    )

    summary = service.get_summary()

    assert summary.total_users == 2
    assert summary.active_users == 1
    assert summary.total_documents == 4
    assert summary.total_conversations == 2
    assert summary.questions_today == audit_repo.count(
        filters=AuditSearchFilter(
            event_type="chat.question.asked",
            date_from=start_of_day,
        )
    )
    assert summary.failed_logins_today == 1
    assert summary.audit_events_today == 3


def test_get_summary_returns_zero_counts_for_empty_database(db_session: Session) -> None:
    document_repo = MagicMock()
    document_repo.count.return_value = 0
    conversation_repo = MagicMock()
    conversation_repo.count.return_value = 0

    service = MonitoringService(
        db=db_session,
        audit_repository=AuditRepository(db_session),
        document_repository=document_repo,
        conversation_repository=conversation_repo,
    )

    summary = service.get_summary()

    assert summary.total_users == 0
    assert summary.active_users == 0
    assert summary.total_documents == 0
    assert summary.total_conversations == 0
    assert summary.questions_today == 0
    assert summary.failed_logins_today == 0
    assert summary.audit_events_today == 0
