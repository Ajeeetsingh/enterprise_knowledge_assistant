"""Unit tests for DashboardService."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.dashboard_repository import DashboardRepository
from app.analytics.schemas.dashboard import DashboardResponse
from app.analytics.services.dashboard_service import DashboardService
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


def test_get_overview_aggregates_inventory_and_chat_metrics(db_session: Session) -> None:
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
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_QUESTION,
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=active_user.id,
    )
    audit_repo.create(
        event_type=AnalyticsEvents.SECURITY_PERMISSION_DENIED,
        event_category=AuditEventCategory.SECURITY,
        action="permission_check",
        status=AuditStatus.FAILED,
        user_id=active_user.id,
    )

    service = DashboardService(DashboardRepository(db_session))
    overview = service.get_overview(context_for_last_n_days(7))
    response = DashboardResponse.from_snapshot(overview)

    assert overview.inventory.total_users == 2
    assert overview.inventory.active_users == 1
    assert overview.chat_metrics.questions_asked == 1
    assert overview.security_events == 1
    assert overview.audit_events == 2
    assert response.chat_metrics.questions_asked == 1
