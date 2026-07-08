"""Unit tests for MonitoringAnalyticsRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.monitoring_repository import MonitoringAnalyticsRepository
from app.analytics.utils.date_filters import context_for_last_n_days
from app.auth import hash_password
from app.db.base import Base
from app.db.models import AuditLog, Conversation, Document, Message, Role, User  # noqa: F401
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.models.message import MessageRole
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


def test_monitoring_repository_aggregates_resources_and_failures(db_session: Session) -> None:
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
            file_size=128,
            checksum=f"checksum-{uuid.uuid4().hex}",
            storage_path="docs/policy.txt",
            status="searchable",
            uploaded_by=user.id,
            owner_id=user.id,
            visibility="public",
        )
    )
    conversation = Conversation(user_id=user.id, title="Ops")
    db_session.add(conversation)
    db_session.commit()

    now = datetime.now(UTC)
    db_session.add_all(
        [
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content="Status check",
                created_at=now,
            ),
            Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content="All good.",
                created_at=now + timedelta(seconds=3),
            ),
        ]
    )
    db_session.commit()

    audit_repo = AuditRepository(db_session)
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_FAILURE,
        event_category=AuditEventCategory.CHAT,
        action="retrieve",
        status=AuditStatus.FAILED,
        user_id=user.id,
        metadata={"reason": "Vector store unavailable"},
    )

    repository = MonitoringAnalyticsRepository(db_session)
    context = context_for_last_n_days(7)

    assert repository.count_total_users() == 1
    assert repository.count_total_documents() == 1
    assert repository.sum_document_storage_bytes() == 128
    assert repository.count_chat_failures(context) == 1
    assert repository.measure_database_query_time_seconds() is not None
    assert repository.compute_chat_latency_samples(context)[0][1] == pytest.approx(3.0)


def test_monitoring_repository_probes_service_statuses(db_session: Session) -> None:
    repository = MonitoringAnalyticsRepository(db_session)
    probes = repository.probe_service_statuses(context_for_last_n_days(7))
    services = {probe.service: probe.status for probe in probes}
    assert services["database"] == "healthy"
    assert services["background_workers"] == "unavailable"
