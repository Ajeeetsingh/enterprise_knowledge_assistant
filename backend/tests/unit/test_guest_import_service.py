"""Unit tests for ConversationService.import_guest_conversation."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import MessageValidationError
from app.db.base import Base
from app.db.models import (  # noqa: F401 — triggers metadata registration
    Conversation,
    Document,
    Message,
    MessageRole,
    Role,
    User,
    user_roles,
)
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.schemas.guest_import import GUEST_IMPORT_MAX_MESSAGES
from app.services.conversation_service import ConversationService
from tests.constants import TEST_PASSWORD_HASH


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _make_user(db: Session) -> User:
    role = Role(name=f"Employee-{uuid.uuid4()}", description="Employee")
    user = User(
        id=uuid.uuid4(),
        email="guest-import@example.com",
        username="guestimport",
        full_name="Guest Import",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user(db_session: Session) -> User:
    return _make_user(db_session)


@pytest.fixture
def service(db_session: Session) -> ConversationService:
    return ConversationService(
        conversation_repo=ConversationRepository(db_session),
        message_repo=MessageRepository(db_session),
    )


class TestImportGuestConversation:
    def test_imports_plain_text_without_citations(
        self, service: ConversationService, user: User, db_session: Session
    ) -> None:
        conversation = service.import_guest_conversation(
            user,
            [
                ("user", "What is RAG?"),
                ("assistant", "RAG is retrieval-augmented generation."),
            ],
        )

        assert conversation.title == "Guest conversation"
        assert conversation.user_id == user.id

        messages = list(
            db_session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.asc())
            )
        )
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER.value
        assert messages[0].content == "What is RAG?"
        assert messages[0].citations == []
        assert messages[0].confidence_score is None
        assert messages[1].role == MessageRole.ASSISTANT.value
        assert messages[1].citations == []
        assert messages[1].confidence_score is None

    def test_rejects_empty_history(
        self, service: ConversationService, user: User
    ) -> None:
        with pytest.raises(MessageValidationError):
            service.import_guest_conversation(user, [])

    def test_rejects_oversized_history(
        self, service: ConversationService, user: User
    ) -> None:
        oversized = [
            ("user", f"q{i}") for i in range(GUEST_IMPORT_MAX_MESSAGES + 1)
        ]
        with pytest.raises(MessageValidationError):
            service.import_guest_conversation(user, oversized)

    def test_rejects_unsupported_role(
        self, service: ConversationService, user: User
    ) -> None:
        with pytest.raises(MessageValidationError):
            service.import_guest_conversation(
                user,
                [("system", "should not import")],  # type: ignore[list-item]
            )

    def test_rolls_back_when_content_invalid(
        self, service: ConversationService, user: User, db_session: Session
    ) -> None:
        with pytest.raises(MessageValidationError):
            service.import_guest_conversation(
                user,
                [
                    ("user", "ok"),
                    ("assistant", "   "),
                ],
            )
        remaining = list(
            db_session.scalars(
                select(Conversation).where(Conversation.user_id == user.id)
            )
        )
        assert remaining == []
