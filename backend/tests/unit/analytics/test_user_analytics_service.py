"""Unit tests for UserAnalyticsService."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.user_repository import UserRepository
from app.analytics.schemas.user import UserAnalyticsOverviewResponse
from app.analytics.services.user_analytics_service import UserAnalyticsService
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


def test_get_overview_returns_dau_wau_mau(db_session: Session) -> None:
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

    service = UserAnalyticsService(UserRepository(db_session))
    overview = service.get_overview(context_for_last_n_days(7))
    response = UserAnalyticsOverviewResponse.from_snapshot(overview)

    assert overview.total_users == 1
    assert overview.new_users == 1
    assert overview.daily_active_users == 1
    assert overview.weekly_active_users == 1
    assert overview.monthly_active_users == 1
    assert overview.average_questions_per_user == pytest.approx(1.0)
    assert response.active_user_percentage == pytest.approx(100.0)


def test_get_trends_returns_chart_series(db_session: Session) -> None:
    user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    AuditRepository(db_session).create(
        event_type=AnalyticsEvents.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
    )

    service = UserAnalyticsService(UserRepository(db_session))
    trends = service.get_trends(context_for_last_n_days(7))

    assert sum(trends.login_activity.points.values()) == 1
    assert sum(trends.user_registrations.points.values()) == 1
