"""Unit tests for UserRepository."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.user_repository import UserRepository
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


def test_count_new_users_and_top_active_users(db_session: Session) -> None:
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
        event_type=AnalyticsEvents.CHAT_QUESTION,
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
    )
    audit_repo.create(
        event_type=AnalyticsEvents.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
    )

    repository = UserRepository(db_session)
    context = context_for_last_n_days(7)

    assert repository.count_new_users(context) == 1
    assert repository.count_distinct_active_users(context) == 1

    top_users, total = repository.list_top_active_users(context, limit=10)
    assert total == 1
    assert top_users[0].email == "active@example.com"
    assert top_users[0].question_count == 1


def test_list_inactive_users_excludes_active_accounts(db_session: Session) -> None:
    active_user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    quiet_user = User(
        email="quiet@example.com",
        username="quiet",
        full_name="Quiet User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    db_session.add_all([active_user, quiet_user])
    db_session.commit()

    AuditRepository(db_session).create(
        event_type=AnalyticsEvents.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.SUCCESS,
        user_id=active_user.id,
    )

    repository = UserRepository(db_session)
    inactive, total = repository.list_inactive_users(
        context_for_last_n_days(7),
        limit=10,
    )

    assert total == 1
    assert len(inactive) == 1
    assert inactive[0].email == "quiet@example.com"
