"""Unit tests for ErrorAnalyticsRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.error_repository import ErrorAnalyticsRepository
from app.analytics.utils.date_filters import context_for_last_n_days
from app.auth import hash_password
from app.db.base import Base
from app.db.models import AuditLog, Conversation, Document, Message, Role, User  # noqa: F401
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository


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


def test_error_repository_aggregates_failures(db_session: Session) -> None:
    user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    audit_repo = AuditRepository(db_session)
    audit_repo.create(
        event_type=AnalyticsEvents.LOGIN_FAILED,
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.FAILED,
    )
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_FAILURE,
        event_category=AuditEventCategory.CHAT,
        action="retrieve",
        status=AuditStatus.FAILED,
        user_id=user.id,
        metadata={"reason": "No documents matched"},
    )
    audit_repo.create(
        event_type=AnalyticsEvents.SECURITY_PERMISSION_DENIED,
        event_category=AuditEventCategory.SECURITY,
        action="permission_check",
        status=AuditStatus.FAILED,
        metadata={"resource": "/api/v1/documents", "required_permission": "read"},
    )
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_QUESTION,
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
    )

    repository = ErrorAnalyticsRepository(db_session)
    context = context_for_last_n_days(7)

    assert repository.count_total_errors(context) == 3
    assert repository.count_authentication_failures(context) == 1
    assert repository.count_authorization_failures(context) == 1
    assert repository.count_retrieval_failures(context) == 1
    assert repository.count_api_errors(context) is None

    endpoints, total = repository.list_endpoint_failures(context, limit=10)
    assert total >= 1
    assert any(item.endpoint == "/api/v1/documents" for item in endpoints)


def test_error_repository_counts_failed_documents(db_session: Session) -> None:
    user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    db_session.add(
        Document(
            id=uuid.uuid4(),
            filename="broken.txt",
            content_type="text/plain",
            file_size=10,
            checksum=f"checksum-{uuid.uuid4().hex}",
            storage_path="docs/broken.txt",
            status="failed",
            uploaded_by=user.id,
            owner_id=user.id,
            visibility="public",
            updated_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    repository = ErrorAnalyticsRepository(db_session)
    context = context_for_last_n_days(7)

    assert repository.count_upload_failures(context) == 1
    assert len(repository.list_upload_failure_timestamps(context)) == 1
