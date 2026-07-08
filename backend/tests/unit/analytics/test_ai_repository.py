"""Unit tests for AIRepository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.ai_repository import AIRepository
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


def test_ai_repository_aggregates_questions_and_failures(db_session: Session) -> None:
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
        event_type=AnalyticsEvents.CHAT_RESPONSE,
        event_category=AuditEventCategory.CHAT,
        action="generate_answer",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
        metadata={"citation_count": 2, "confidence_score": 0.91},
    )
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_FAILURE,
        event_category=AuditEventCategory.CHAT,
        action="retrieve",
        status=AuditStatus.FAILED,
        user_id=user.id,
        metadata={"reason": "Vector store unavailable"},
    )

    repository = AIRepository(db_session)
    context = context_for_last_n_days(7)

    assert repository.count_questions(context) == 1
    assert repository.count_responses(context) == 1
    assert repository.count_failures(context) == 1
    assert repository.average_citation_count(context) == pytest.approx(2.0)
    assert repository.average_confidence_score(context) == pytest.approx(0.91)


def test_ai_repository_computes_response_time_and_top_questions(db_session: Session) -> None:
    user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    conversation = Conversation(user_id=user.id, title="Benefits")
    db_session.add(conversation)
    db_session.commit()

    now = datetime.now(UTC)
    db_session.add_all(
        [
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content="What is the leave policy?",
                created_at=now,
            ),
            Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content="You receive 20 days of leave.",
                citations=[{"source": "policy.txt", "excerpt": "20 days", "confidence": 0.9}],
                confidence_score=0.88,
                created_at=now + timedelta(seconds=4),
            ),
        ]
    )
    db_session.commit()

    repository = AIRepository(db_session)
    context = context_for_last_n_days(7)
    samples = repository.compute_response_time_samples(context)
    top_questions, total = repository.list_top_questions(context, limit=5)

    assert len(samples) == 1
    assert samples[0][1] == pytest.approx(4.0)
    assert total == 1
    assert top_questions[0].question == "What is the leave policy?"
