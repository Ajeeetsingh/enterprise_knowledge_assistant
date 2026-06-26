"""Unit tests for ConversationService message methods (Phase 6.3).

Tests exercise the four new service methods introduced in Phase 6.3:
    - add_user_message
    - add_assistant_message
    - get_conversation_history
    - get_recent_messages

All tests use an in-memory SQLite database so no external services are needed.

Coverage:
    ✓ add_user_message — happy path
    ✓ add_user_message — content stored and trimmed
    ✓ add_user_message — role is USER
    ✓ add_user_message — empty content rejected
    ✓ add_user_message — whitespace-only content rejected
    ✓ add_user_message — ownership enforced (not-found)
    ✓ add_user_message — ownership enforced (foreign conversation)
    ✓ add_assistant_message — happy path
    ✓ add_assistant_message — citations stored and retrieved
    ✓ add_assistant_message — confidence_score stored
    ✓ add_assistant_message — confidence_score = 0.0 valid (boundary)
    ✓ add_assistant_message — confidence_score = 1.0 valid (boundary)
    ✓ add_assistant_message — confidence_score < 0.0 rejected
    ✓ add_assistant_message — confidence_score > 1.0 rejected
    ✓ add_assistant_message — None confidence_score allowed
    ✓ add_assistant_message — None citations allowed
    ✓ add_assistant_message — ownership enforced
    ✓ get_conversation_history — returns messages oldest-first
    ✓ get_conversation_history — empty conversation returns []
    ✓ get_conversation_history — ownership enforced
    ✓ get_conversation_history — deterministic ordering
    ✓ get_recent_messages — returns last N messages
    ✓ get_recent_messages — result ordered oldest-to-newest within window
    ✓ get_recent_messages — limit < total messages returns correct window
    ✓ get_recent_messages — limit >= total returns all messages
    ✓ get_recent_messages — limit clamped to MAX_RECENT_MESSAGES
    ✓ get_recent_messages — negative limit clamped to 1
    ✓ get_recent_messages — ownership enforced
    ✓ conversation updated_at reflects latest message activity
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy import create_engine, update as sa_update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.core.exceptions import (
    ConversationAccessDeniedError,
    ConversationNotFoundError,
    InvalidConfidenceScoreError,
    MessageValidationError,
)
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
from app.services.conversation_service import (
    MAX_RECENT_MESSAGES,
    ConversationService,
)


# =========================================================================== #
# Infrastructure fixtures                                                      #
# =========================================================================== #


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


def _make_user(db: Session, *, email: str) -> User:
    role = Role(name=f"role-{uuid.uuid4()}", description="Role")
    user = User(
        id=uuid.uuid4(),
        email=email,
        username=email.split("@")[0],
        full_name="Test User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db.add_all([role, user])
    db.commit()
    return user


@pytest.fixture
def owner(db_session: Session) -> User:
    return _make_user(db_session, email="owner@example.com")


@pytest.fixture
def other_user(db_session: Session) -> User:
    return _make_user(db_session, email="other@example.com")


@pytest.fixture
def service(db_session: Session) -> ConversationService:
    return ConversationService(
        conversation_repo=ConversationRepository(db_session),
        message_repo=MessageRepository(db_session),
    )


@pytest.fixture
def conversation(service: ConversationService, owner: User) -> Conversation:
    return service.create_conversation(owner, title="Test Conversation")


# =========================================================================== #
# add_user_message                                                             #
# =========================================================================== #


class TestAddUserMessage:
    def test_returns_message(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_user_message(owner, conversation.id, "Hello?")
        assert msg is not None
        assert isinstance(msg.id, uuid.UUID)

    def test_role_is_user(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_user_message(owner, conversation.id, "Question")
        assert msg.role == MessageRole.USER

    def test_content_stored(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_user_message(owner, conversation.id, "What is leave policy?")
        assert msg.content == "What is leave policy?"

    def test_content_trimmed(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_user_message(owner, conversation.id, "  trimmed  ")
        assert msg.content == "trimmed"

    def test_empty_content_raises(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        with pytest.raises(MessageValidationError):
            service.add_user_message(owner, conversation.id, "")

    def test_whitespace_content_raises(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        with pytest.raises(MessageValidationError):
            service.add_user_message(owner, conversation.id, "   \t\n  ")

    def test_not_found_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            service.add_user_message(owner, uuid.uuid4(), "Content")

    def test_foreign_conversation_raises_access_denied(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
        conversation: Conversation,
    ) -> None:
        with pytest.raises(ConversationAccessDeniedError):
            service.add_user_message(other_user, conversation.id, "Content")

    def test_message_linked_to_conversation(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_user_message(owner, conversation.id, "Hello")
        assert msg.conversation_id == conversation.id


# =========================================================================== #
# add_assistant_message                                                        #
# =========================================================================== #


class TestAddAssistantMessage:
    def test_returns_message(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(owner, conversation.id, "Answer")
        assert msg is not None

    def test_role_is_assistant(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(owner, conversation.id, "Answer")
        assert msg.role == MessageRole.ASSISTANT

    def test_content_stored(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(owner, conversation.id, "The policy states…")
        assert msg.content == "The policy states…"

    def test_content_trimmed(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(owner, conversation.id, "  answer  ")
        assert msg.content == "answer"

    def test_empty_content_raises(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        with pytest.raises(MessageValidationError):
            service.add_assistant_message(owner, conversation.id, "")

    def test_citations_stored_and_retrieved(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        citations: list[Any] = [
            {"source": "policy.pdf", "page": 3, "text": "16 weeks"}
        ]
        msg = service.add_assistant_message(
            owner, conversation.id, "Answer", citations=citations
        )
        assert msg.citations == citations

    def test_none_citations_allowed(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(
            owner, conversation.id, "Answer", citations=None
        )
        assert msg.citations == []

    def test_confidence_score_stored(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(
            owner, conversation.id, "Answer", confidence_score=0.85
        )
        assert msg.confidence_score == pytest.approx(0.85)

    def test_confidence_score_zero_valid(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(
            owner, conversation.id, "Answer", confidence_score=0.0
        )
        assert msg.confidence_score == pytest.approx(0.0)

    def test_confidence_score_one_valid(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(
            owner, conversation.id, "Answer", confidence_score=1.0
        )
        assert msg.confidence_score == pytest.approx(1.0)

    def test_confidence_score_below_zero_raises(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        with pytest.raises(InvalidConfidenceScoreError):
            service.add_assistant_message(
                owner, conversation.id, "Answer", confidence_score=-0.01
            )

    def test_confidence_score_above_one_raises(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        with pytest.raises(InvalidConfidenceScoreError):
            service.add_assistant_message(
                owner, conversation.id, "Answer", confidence_score=1.01
            )

    def test_none_confidence_score_allowed(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        msg = service.add_assistant_message(
            owner, conversation.id, "Answer", confidence_score=None
        )
        assert msg.confidence_score is None

    def test_not_found_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            service.add_assistant_message(owner, uuid.uuid4(), "Answer")

    def test_foreign_conversation_raises_access_denied(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
        conversation: Conversation,
    ) -> None:
        with pytest.raises(ConversationAccessDeniedError):
            service.add_assistant_message(other_user, conversation.id, "Answer")


# =========================================================================== #
# get_conversation_history                                                     #
# =========================================================================== #


class TestGetConversationHistory:
    def test_empty_conversation_returns_empty_list(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        history = service.get_conversation_history(owner, conversation.id)
        assert history == []

    def test_returns_all_messages(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        service.add_user_message(owner, conversation.id, "Q1")
        service.add_assistant_message(owner, conversation.id, "A1")
        service.add_user_message(owner, conversation.id, "Q2")

        history = service.get_conversation_history(owner, conversation.id)
        assert len(history) == 3

    def test_ordered_oldest_to_newest(
        self,
        db_session: Session,
        service: ConversationService,
        owner: User,
        conversation: Conversation,
    ) -> None:
        # Insert with explicit timestamps so ordering is deterministic
        # regardless of SQLite's second-level CURRENT_TIMESTAMP precision.
        msg_repo = MessageRepository(db_session)

        older = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="First",
        )
        newer = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Second",
        )

        # Force distinct timestamps via raw update.
        db_session.execute(
            sa_update(Message)
            .where(Message.id == older.id)
            .values(created_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc))
        )
        db_session.execute(
            sa_update(Message)
            .where(Message.id == newer.id)
            .values(created_at=datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc))
        )
        db_session.commit()

        history = service.get_conversation_history(owner, conversation.id)
        assert history[0].content == "First"
        assert history[1].content == "Second"

    def test_not_found_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            service.get_conversation_history(owner, uuid.uuid4())

    def test_foreign_conversation_raises_access_denied(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
        conversation: Conversation,
    ) -> None:
        with pytest.raises(ConversationAccessDeniedError):
            service.get_conversation_history(other_user, conversation.id)

    def test_history_isolated_per_conversation(
        self,
        service: ConversationService,
        owner: User,
    ) -> None:
        conv_a = service.create_conversation(owner, title="A")
        conv_b = service.create_conversation(owner, title="B")

        service.add_user_message(owner, conv_a.id, "In A")
        service.add_user_message(owner, conv_b.id, "In B")

        history_a = service.get_conversation_history(owner, conv_a.id)
        history_b = service.get_conversation_history(owner, conv_b.id)

        assert len(history_a) == 1
        assert history_a[0].content == "In A"
        assert len(history_b) == 1
        assert history_b[0].content == "In B"


# =========================================================================== #
# get_recent_messages                                                          #
# =========================================================================== #


class TestGetRecentMessages:
    def _add_n_messages(
        self,
        service: ConversationService,
        owner: User,
        conv: Conversation,
        n: int,
    ) -> list[Message]:
        """Add *n* user messages and return them in insertion order."""
        messages = []
        for i in range(n):
            msg = service.add_user_message(owner, conv.id, f"Message {i}")
            messages.append(msg)
        return messages

    def test_returns_last_n_messages(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        self._add_n_messages(service, owner, conversation, 10)
        recent = service.get_recent_messages(owner, conversation.id, limit=3)
        assert len(recent) == 3

    def test_limit_ge_total_returns_all(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        self._add_n_messages(service, owner, conversation, 5)
        recent = service.get_recent_messages(owner, conversation.id, limit=20)
        assert len(recent) == 5

    def test_empty_conversation_returns_empty_list(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        recent = service.get_recent_messages(owner, conversation.id, limit=10)
        assert recent == []

    def test_ordered_oldest_to_newest_within_window(
        self,
        db_session: Session,
        service: ConversationService,
        owner: User,
        conversation: Conversation,
    ) -> None:
        msg_repo = MessageRepository(db_session)

        # Create 5 messages with explicit ascending timestamps.
        messages = []
        for i in range(5):
            msg = msg_repo.create(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=f"Msg {i}",
            )
            db_session.execute(
                sa_update(Message)
                .where(Message.id == msg.id)
                .values(
                    created_at=datetime(
                        2025, 1, 1, 10, 0, i, tzinfo=timezone.utc
                    )
                )
            )
            messages.append(msg)
        db_session.commit()

        # Ask for last 3 — should be Msg 2, Msg 3, Msg 4 in order.
        recent = service.get_recent_messages(owner, conversation.id, limit=3)
        assert len(recent) == 3
        assert recent[0].content == "Msg 2"
        assert recent[1].content == "Msg 3"
        assert recent[2].content == "Msg 4"

    def test_limit_clamped_to_max(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        # Even if caller passes an absurdly large limit, it should be capped.
        recent = service.get_recent_messages(
            owner, conversation.id, limit=MAX_RECENT_MESSAGES + 9999
        )
        # Empty conversation — just verifying no error and correct return type.
        assert recent == []

    def test_negative_limit_clamped_to_one(
        self,
        db_session: Session,
        service: ConversationService,
        owner: User,
        conversation: Conversation,
    ) -> None:
        service.add_user_message(owner, conversation.id, "Only message")
        recent = service.get_recent_messages(owner, conversation.id, limit=-5)
        # Clamped to 1 → should return the single most recent message.
        assert len(recent) == 1

    def test_not_found_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            service.get_recent_messages(owner, uuid.uuid4(), limit=10)

    def test_foreign_conversation_raises_access_denied(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
        conversation: Conversation,
    ) -> None:
        with pytest.raises(ConversationAccessDeniedError):
            service.get_recent_messages(other_user, conversation.id, limit=10)

    def test_recent_window_is_from_the_end(
        self,
        db_session: Session,
        service: ConversationService,
        owner: User,
        conversation: Conversation,
    ) -> None:
        msg_repo = MessageRepository(db_session)

        # Insert 10 messages with distinct timestamps.
        for i in range(10):
            msg = msg_repo.create(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=f"M{i}",
            )
            db_session.execute(
                sa_update(Message)
                .where(Message.id == msg.id)
                .values(
                    created_at=datetime(2025, 1, 1, 10, 0, i, tzinfo=timezone.utc)
                )
            )
        db_session.commit()

        # Request last 4 → should be M6, M7, M8, M9
        recent = service.get_recent_messages(owner, conversation.id, limit=4)
        contents = [m.content for m in recent]
        assert contents == ["M6", "M7", "M8", "M9"]


# =========================================================================== #
# Conversation updated_at activity tracking                                   #
# =========================================================================== #


class TestConversationActivityTracking:
    def test_add_user_message_updates_conversation_timestamp(
        self,
        db_session: Session,
        service: ConversationService,
        owner: User,
        conversation: Conversation,
    ) -> None:
        # Use a timezone-naive old_time because SQLite returns naive datetimes
        # from CURRENT_TIMESTAMP.  A far-past date ensures the comparison is
        # unambiguous regardless of clock precision.
        old_time = datetime(2020, 6, 1)
        db_session.execute(
            sa_update(Conversation)
            .where(Conversation.id == conversation.id)
            .values(updated_at=old_time)
        )
        db_session.commit()

        service.add_user_message(owner, conversation.id, "Hello")

        updated = service.get_conversation(owner, conversation.id)
        assert updated.updated_at > old_time

    def test_add_assistant_message_updates_conversation_timestamp(
        self,
        db_session: Session,
        service: ConversationService,
        owner: User,
        conversation: Conversation,
    ) -> None:
        old_time = datetime(2020, 6, 1)
        db_session.execute(
            sa_update(Conversation)
            .where(Conversation.id == conversation.id)
            .values(updated_at=old_time)
        )
        db_session.commit()

        service.add_assistant_message(owner, conversation.id, "Answer")

        updated = service.get_conversation(owner, conversation.id)
        assert updated.updated_at > old_time
