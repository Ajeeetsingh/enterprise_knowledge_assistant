"""Unit tests for KnowledgeRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.constants import AnalyticsEvents
from app.analytics.repositories.knowledge_repository import KnowledgeRepository
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


def _seed_knowledge_data(db_session: Session, user: User) -> Document:
    document = Document(
        id=uuid.uuid4(),
        filename="policy.txt",
        content_type="text/plain",
        file_size=10,
        checksum=f"checksum-{uuid.uuid4().hex}",
        storage_path="docs/policy.txt",
        status="searchable",
        uploaded_by=user.id,
        owner_id=user.id,
        department="HR",
        visibility="public",
    )
    unused_document = Document(
        id=uuid.uuid4(),
        filename="archive.txt",
        content_type="text/plain",
        file_size=10,
        checksum=f"checksum-{uuid.uuid4().hex}",
        storage_path="docs/archive.txt",
        status="searchable",
        uploaded_by=user.id,
        owner_id=user.id,
        department="Finance",
        visibility="public",
        updated_at=datetime.now(UTC) - timedelta(days=120),
    )
    db_session.add_all([document, unused_document])

    conversation = Conversation(user_id=user.id, title="HR")
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
                created_at=now + timedelta(seconds=2),
            ),
        ]
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
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_RESPONSE,
        event_category=AuditEventCategory.CHAT,
        action="generate_answer",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
        metadata={"citation_count": 1},
    )
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_FAILURE,
        event_category=AuditEventCategory.CHAT,
        action="retrieve",
        status=AuditStatus.FAILED,
        user_id=user.id,
        metadata={"reason": "No documents matched"},
    )
    return document


def test_knowledge_repository_aggregates_document_and_search_metrics(
    db_session: Session,
) -> None:
    user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    _seed_knowledge_data(db_session, user)
    repository = KnowledgeRepository(db_session, stale_days=90)
    context = context_for_last_n_days(7)

    assert repository.count_total_documents() == 2
    assert repository.count_active_documents() == 2
    assert repository.count_unused_documents(context) == 1
    assert repository.average_citations_per_document(context) == pytest.approx(1.0)

    top_documents, total = repository.list_top_documents(context, limit=5)
    assert total == 1
    assert top_documents[0].filename == "policy.txt"
    assert top_documents[0].citation_count == 1

    popularity = repository.collection_popularity(context)
    assert popularity["HR"] == 1
    assert repository.search_success_rate(context) == pytest.approx(0.0)


def test_knowledge_repository_lists_freshness_and_gaps(db_session: Session) -> None:
    user = User(
        email="active@example.com",
        username="active",
        full_name="Active User",
        password_hash=hash_password("secret"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    _seed_knowledge_data(db_session, user)
    repository = KnowledgeRepository(db_session, stale_days=90)
    context = context_for_last_n_days(7)

    never_cited, never_cited_total = repository.list_never_cited_documents(
        context,
        limit=10,
    )
    assert never_cited_total == 1
    assert never_cited[0].filename == "archive.txt"

    recent_uploads, recent_total = repository.list_recent_uploads(context, limit=10)
    assert recent_total == 2
    assert len(recent_uploads) == 2

    oldest, oldest_total = repository.list_oldest_documents(limit=10)
    assert oldest_total == 2
    assert oldest[0].filename == "archive.txt" or oldest[0].filename == "policy.txt"
