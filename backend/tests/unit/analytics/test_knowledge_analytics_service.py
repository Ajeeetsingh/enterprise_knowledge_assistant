"""Unit tests for KnowledgeAnalyticsService."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.repositories.knowledge_repository import KnowledgeRepository
from app.analytics.schemas.knowledge import KnowledgeOverviewResponse
from app.analytics.services.knowledge_analytics_service import KnowledgeAnalyticsService
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


def test_get_overview_returns_knowledge_kpis(db_session: Session) -> None:
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

    audit_repo = AuditRepository(db_session)
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_QUESTION,
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
    )

    service = KnowledgeAnalyticsService(KnowledgeRepository(db_session))
    overview = service.get_overview(context_for_last_n_days(7))
    response = KnowledgeOverviewResponse.from_snapshot(overview)

    assert overview.total_documents == 1
    assert overview.active_documents == 1
    assert response.search_success_rate == pytest.approx(100.0)
