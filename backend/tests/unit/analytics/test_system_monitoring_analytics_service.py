"""Unit tests for SystemMonitoringAnalyticsService."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.repositories.monitoring_repository import MonitoringAnalyticsRepository
from app.analytics.schemas.monitoring import SystemHealthOverviewResponse
from app.analytics.services.monitoring_service import SystemMonitoringAnalyticsService
from app.analytics.utils.date_filters import context_for_last_n_days
from app.auth import hash_password
from app.db.base import Base
from app.db.models import AuditLog, Conversation, Document, Message, Role, User  # noqa: F401
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.analytics.constants import AnalyticsEvents
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


def test_get_overview_returns_system_health(db_session: Session) -> None:
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
            filename="policy.txt",
            content_type="text/plain",
            file_size=10,
            checksum=f"checksum-{uuid.uuid4().hex}",
            storage_path="docs/policy.txt",
            status="searchable",
            uploaded_by=user.id,
            owner_id=user.id,
            visibility="public",
        )
    )
    db_session.commit()

    service = SystemMonitoringAnalyticsService(MonitoringAnalyticsRepository(db_session))
    overview = service.get_overview(context_for_last_n_days(7))
    response = SystemHealthOverviewResponse.from_snapshot(overview)

    assert response.api_health == "healthy"
    assert response.database_health == "healthy"
    assert overview.uptime_seconds >= 0


def test_get_performance_returns_null_for_uninstrumented_metrics(db_session: Session) -> None:
    service = SystemMonitoringAnalyticsService(MonitoringAnalyticsRepository(db_session))
    performance = service.get_performance(context_for_last_n_days(7))

    assert performance.average_api_response_time_seconds is None
    assert performance.average_retrieval_time_seconds is None
    assert performance.embedding_generation_time_seconds is None
    assert performance.database_query_time_seconds is not None
