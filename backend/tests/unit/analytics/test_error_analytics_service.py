"""Unit tests for ErrorAnalyticsService."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.error_repository import ErrorAnalyticsRepository
from app.analytics.schemas.error import ErrorOverviewResponse
from app.analytics.services.error_analytics_service import ErrorAnalyticsService
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


def test_get_overview_calculates_error_rates(db_session: Session) -> None:
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
        event_type=AnalyticsEvents.CHAT_QUESTION,
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
    )

    service = ErrorAnalyticsService(ErrorAnalyticsRepository(db_session))
    overview = service.get_overview(context_for_last_n_days(7))
    response = ErrorOverviewResponse.from_snapshot(overview)

    assert overview.total_errors == 1
    assert overview.api_errors is None
    assert response.error_rate == pytest.approx(50.0)
    assert response.error_free_requests_percentage == pytest.approx(50.0)
