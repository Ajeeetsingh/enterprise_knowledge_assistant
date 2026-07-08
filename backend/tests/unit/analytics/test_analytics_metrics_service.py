"""Unit tests for AnalyticsMetricsService."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.dashboard_repository import DashboardRepository
from app.analytics.services.metrics_service import AnalyticsMetricsService
from app.analytics.utils.date_filters import context_for_last_n_days
from app.auth import hash_password
from app.db.base import Base
from app.db.models import AuditLog, Conversation, Document, Role, User  # noqa: F401
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


def test_get_active_user_metrics_returns_dau_wau_mau(db_session: Session) -> None:
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
        event_type=AnalyticsEvents.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
    )

    service = AnalyticsMetricsService(DashboardRepository(db_session))
    metrics = service.get_active_user_metrics(context=context_for_last_n_days(7))

    assert metrics.daily_active_users == 1
    assert metrics.weekly_active_users == 1
    assert metrics.monthly_active_users == 1


def test_get_daily_event_series_buckets_by_day(db_session: Session) -> None:
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

    service = AnalyticsMetricsService(DashboardRepository(db_session))
    series = service.get_daily_event_series(
        AnalyticsEvents.CHAT_QUESTION,
        context_for_last_n_days(7),
    )

    assert sum(series.values()) == 1
