"""Unit tests for ConversationRepository and MessageRepository (Phase 6.1).

Tests use an in-memory SQLite database so no running PostgreSQL instance is
required.  The full ORM model graph (User → Conversation → Message) is
exercised through repository operations only — no service layer is involved.

Coverage:
    ✓ Conversation creation
    ✓ Message creation
    ✓ User → Conversation relationship
    ✓ Conversation → Message relationship
    ✓ Cascade deletion (conversation → messages)
    ✓ Cascade deletion (user → conversations → messages)
    ✓ ConversationRepository.get_by_id
    ✓ ConversationRepository.list_by_user (pagination, ordering)
    ✓ ConversationRepository.delete
    ✓ MessageRepository.list_for_conversation (ordering)
    ✓ MessageRole enum values
    ✓ citations property serialization
    ✓ confidence_score persistence
    ✓ title nullable field
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.db.base import Base
from app.db.models import (  # noqa: F401 — imports trigger metadata registration
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


# =========================================================================== #
# Fixtures                                                                     #
# =========================================================================== #


@pytest.fixture
def db_session() -> Session:
    """Provide a fresh in-memory SQLite session for each test."""
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


@pytest.fixture
def user(db_session: Session) -> User:
    """Create and persist a test user with an Admin role."""
    role = Role(name="Admin", description="Administrator")
    u = User(
        id=uuid.uuid4(),
        email="user@example.com",
        username="testuser",
        full_name="Test User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    u.roles.append(role)
    db_session.add_all([role, u])
    db_session.commit()
    return u


@pytest.fixture
def second_user(db_session: Session) -> User:
    """Create a second user for isolation tests."""
    role = Role(name="Employee", description="Employee")
    u = User(
        id=uuid.uuid4(),
        email="other@example.com",
        username="otheruser",
        full_name="Other User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    u.roles.append(role)
    db_session.add_all([role, u])
    db_session.commit()
    return u


@pytest.fixture
def conv_repo(db_session: Session) -> ConversationRepository:
    return ConversationRepository(db_session)


@pytest.fixture
def msg_repo(db_session: Session) -> MessageRepository:
    return MessageRepository(db_session)


@pytest.fixture
def conversation(
    conv_repo: ConversationRepository,
    user: User,
) -> Conversation:
    """Create a default conversation owned by *user*."""
    return conv_repo.create(user_id=user.id, title="Test Conversation")


# =========================================================================== #
# MessageRole enum                                                             #
# =========================================================================== #


class TestMessageRoleEnum:
    def test_user_role_value(self) -> None:
        assert MessageRole.USER == "user"

    def test_assistant_role_value(self) -> None:
        assert MessageRole.ASSISTANT == "assistant"

    def test_system_role_value(self) -> None:
        assert MessageRole.SYSTEM == "system"

    def test_role_is_str_enum(self) -> None:
        assert isinstance(MessageRole.USER, str)

    def test_all_roles_defined(self) -> None:
        values = {r.value for r in MessageRole}
        assert values == {"user", "assistant", "system"}


# =========================================================================== #
# Conversation creation                                                        #
# =========================================================================== #


class TestConversationCreation:
    def test_create_returns_conversation(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        conv = conv_repo.create(user_id=user.id, title="HR Policies")
        assert conv is not None
        assert isinstance(conv.id, uuid.UUID)

    def test_create_persists_user_id(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        conv = conv_repo.create(user_id=user.id)
        assert conv.user_id == user.id

    def test_create_with_title(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        conv = conv_repo.create(user_id=user.id, title="Finance Q&A")
        assert conv.title == "Finance Q&A"

    def test_create_without_title(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        conv = conv_repo.create(user_id=user.id)
        assert conv.title is None

    def test_create_sets_timestamps(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        conv = conv_repo.create(user_id=user.id)
        assert conv.created_at is not None
        assert conv.updated_at is not None

    def test_create_assigns_unique_ids(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        a = conv_repo.create(user_id=user.id)
        b = conv_repo.create(user_id=user.id)
        assert a.id != b.id


# =========================================================================== #
# ConversationRepository — get_by_id                                          #
# =========================================================================== #


class TestConversationGetById:
    def test_get_existing_conversation(
        self,
        conv_repo: ConversationRepository,
        conversation: Conversation,
    ) -> None:
        found = conv_repo.get_by_id(conversation.id)
        assert found is not None
        assert found.id == conversation.id

    def test_get_nonexistent_returns_none(
        self, conv_repo: ConversationRepository
    ) -> None:
        result = conv_repo.get_by_id(uuid.uuid4())
        assert result is None


# =========================================================================== #
# ConversationRepository — list_by_user                                       #
# =========================================================================== #


class TestConversationListByUser:
    def test_list_returns_only_user_conversations(
        self,
        conv_repo: ConversationRepository,
        user: User,
        second_user: User,
    ) -> None:
        conv_repo.create(user_id=user.id)
        conv_repo.create(user_id=user.id)
        conv_repo.create(user_id=second_user.id)

        results, total = conv_repo.list_by_user(user.id)
        assert total == 2
        assert all(c.user_id == user.id for c in results)

    def test_list_empty_for_new_user(
        self, conv_repo: ConversationRepository, second_user: User
    ) -> None:
        results, total = conv_repo.list_by_user(second_user.id)
        assert results == []
        assert total == 0

    def test_list_ordered_newest_first(
        self,
        db_session: Session,
        conv_repo: ConversationRepository,
        user: User,
    ) -> None:
        from datetime import datetime, timezone

        # Insert conversations with explicit, distinct created_at values to
        # verify ordering without relying on SQLite's second-level CURRENT_TIMESTAMP.
        older_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        newer_time = datetime(2025, 1, 1, 13, 0, 0, tzinfo=timezone.utc)

        first = Conversation(id=uuid.uuid4(), user_id=user.id, title="First")
        first.created_at = older_time
        first.updated_at = older_time

        second = Conversation(id=uuid.uuid4(), user_id=user.id, title="Second")
        second.created_at = newer_time
        second.updated_at = newer_time

        db_session.add_all([first, second])
        db_session.commit()

        results, _ = conv_repo.list_by_user(user.id)
        ids = [c.id for c in results]
        # Newest (second) comes before oldest (first) in descending order.
        assert ids.index(second.id) < ids.index(first.id)

    def test_list_pagination_limit(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        for i in range(5):
            conv_repo.create(user_id=user.id, title=f"Conv {i}")

        results, total = conv_repo.list_by_user(user.id, limit=3, offset=0)
        assert total == 5
        assert len(results) == 3

    def test_list_pagination_offset(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        for i in range(5):
            conv_repo.create(user_id=user.id, title=f"Conv {i}")

        results, total = conv_repo.list_by_user(user.id, limit=10, offset=3)
        assert total == 5
        assert len(results) == 2

    def test_list_total_reflects_all_records(
        self, conv_repo: ConversationRepository, user: User
    ) -> None:
        for _ in range(4):
            conv_repo.create(user_id=user.id)

        _, total = conv_repo.list_by_user(user.id, limit=2, offset=0)
        assert total == 4


# =========================================================================== #
# ConversationRepository — update_title (Phase 6.7)                            #
# =========================================================================== #


class TestConversationUpdateTitle:
    def test_update_title_persists(
        self,
        conv_repo: ConversationRepository,
        conversation: Conversation,
    ) -> None:
        updated = conv_repo.update_title(conversation.id, "Renamed Title")
        assert updated is not None
        assert updated.title == "Renamed Title"

        fetched = conv_repo.get_by_id(conversation.id)
        assert fetched is not None
        assert fetched.title == "Renamed Title"

    def test_update_title_returns_none_when_missing(
        self, conv_repo: ConversationRepository
    ) -> None:
        assert conv_repo.update_title(uuid.uuid4(), "Missing") is None

    def test_update_title_refreshes_updated_at(
        self,
        conv_repo: ConversationRepository,
        conversation: Conversation,
    ) -> None:
        original_updated_at = conversation.updated_at
        updated = conv_repo.update_title(conversation.id, "Renamed Title")
        assert updated is not None
        assert updated.updated_at >= original_updated_at


# =========================================================================== #
# ConversationRepository — set_title_if_unset (auto-title generation)          #
# =========================================================================== #


class TestConversationSetTitleIfUnset:
    def test_sets_title_when_currently_unset(
        self,
        conv_repo: ConversationRepository,
        user: User,
    ) -> None:
        conv = conv_repo.create(user_id=user.id, title=None)

        updated = conv_repo.set_title_if_unset(conv.id, "Commercial Paper Issuers")

        assert updated is not None
        assert updated.title == "Commercial Paper Issuers"
        fetched = conv_repo.get_by_id(conv.id)
        assert fetched is not None
        assert fetched.title == "Commercial Paper Issuers"

    def test_does_not_overwrite_existing_title(
        self,
        conv_repo: ConversationRepository,
        conversation: Conversation,
    ) -> None:
        result = conv_repo.set_title_if_unset(conversation.id, "New Auto Title")

        assert result is None
        fetched = conv_repo.get_by_id(conversation.id)
        assert fetched is not None
        assert fetched.title == "Test Conversation"

    def test_returns_none_when_conversation_missing(
        self,
        conv_repo: ConversationRepository,
    ) -> None:
        assert conv_repo.set_title_if_unset(uuid.uuid4(), "Anything") is None

    def test_second_call_is_a_no_op(
        self,
        conv_repo: ConversationRepository,
        user: User,
    ) -> None:
        conv = conv_repo.create(user_id=user.id, title=None)

        first = conv_repo.set_title_if_unset(conv.id, "First Title")
        second = conv_repo.set_title_if_unset(conv.id, "Second Title")

        assert first is not None
        assert second is None
        fetched = conv_repo.get_by_id(conv.id)
        assert fetched is not None
        assert fetched.title == "First Title"


# =========================================================================== #
# ConversationRepository — delete                                              #
# =========================================================================== #


class TestConversationDelete:
    def test_delete_returns_true(
        self,
        conv_repo: ConversationRepository,
        conversation: Conversation,
    ) -> None:
        assert conv_repo.delete(conversation.id) is True

    def test_delete_removes_conversation(
        self,
        conv_repo: ConversationRepository,
        conversation: Conversation,
    ) -> None:
        conv_repo.delete(conversation.id)
        assert conv_repo.get_by_id(conversation.id) is None

    def test_delete_nonexistent_returns_false(
        self, conv_repo: ConversationRepository
    ) -> None:
        assert conv_repo.delete(uuid.uuid4()) is False


# =========================================================================== #
# Message creation                                                             #
# =========================================================================== #


class TestMessageCreation:
    def test_create_user_message(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="What is the leave policy?",
        )
        assert msg is not None
        assert isinstance(msg.id, uuid.UUID)
        assert msg.role == MessageRole.USER

    def test_create_assistant_message(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="The leave policy states...",
            confidence_score=0.92,
        )
        assert msg.role == MessageRole.ASSISTANT
        assert msg.confidence_score == pytest.approx(0.92)

    def test_create_message_with_citations(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        citations = [
            {"source": "hr_policy.pdf", "page": 3, "text": "16 weeks paid"},
        ]
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="According to HR policy...",
            citations=citations,
        )
        assert msg.citations == citations

    def test_create_message_without_citations(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hello",
        )
        assert msg.citations == []

    def test_create_message_without_confidence_score(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hello",
        )
        assert msg.confidence_score is None

    def test_create_persists_conversation_id(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Test",
        )
        assert msg.conversation_id == conversation.id

    def test_create_with_string_role(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role="assistant",
            content="Answer",
        )
        assert msg.role == "assistant"
        assert msg.role_enum is MessageRole.ASSISTANT

    def test_create_sets_timestamp(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hi",
        )
        assert msg.created_at is not None


# =========================================================================== #
# MessageRepository — list_for_conversation                                   #
# =========================================================================== #


class TestMessageListForConversation:
    def test_list_returns_all_messages(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Q1",
        )
        msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="A1",
        )
        messages = msg_repo.list_for_conversation(conversation.id)
        assert len(messages) == 2

    def test_list_returns_empty_for_new_conversation(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        messages = msg_repo.list_for_conversation(conversation.id)
        assert messages == []

    def test_list_ordered_oldest_first(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        first = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="First",
        )
        second = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Second",
        )
        messages = msg_repo.list_for_conversation(conversation.id)
        assert messages[0].id == first.id
        assert messages[1].id == second.id

    def test_list_only_returns_messages_for_that_conversation(
        self,
        conv_repo: ConversationRepository,
        msg_repo: MessageRepository,
        user: User,
        conversation: Conversation,
    ) -> None:
        other = conv_repo.create(user_id=user.id, title="Other")
        msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Mine",
        )
        msg_repo.create(
            conversation_id=other.id,
            role=MessageRole.USER,
            content="Not mine",
        )
        messages = msg_repo.list_for_conversation(conversation.id)
        assert len(messages) == 1
        assert messages[0].content == "Mine"


# =========================================================================== #
# Cascade deletion                                                             #
# =========================================================================== #


class TestCascadeDeletion:
    def test_deleting_conversation_removes_messages(
        self,
        conv_repo: ConversationRepository,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Will be deleted",
        )
        msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Also deleted",
        )
        conv_repo.delete(conversation.id)
        remaining = msg_repo.list_for_conversation(conversation.id)
        assert remaining == []

    def test_deleting_user_removes_conversations(
        self,
        db_session: Session,
        conv_repo: ConversationRepository,
        user: User,
        conversation: Conversation,
    ) -> None:
        assert conv_repo.get_by_id(conversation.id) is not None
        db_session.delete(user)
        db_session.commit()
        assert conv_repo.get_by_id(conversation.id) is None

    def test_deleting_user_removes_all_nested_messages(
        self,
        db_session: Session,
        conv_repo: ConversationRepository,
        msg_repo: MessageRepository,
        user: User,
        conversation: Conversation,
    ) -> None:
        msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Nested message",
        )
        db_session.delete(user)
        db_session.commit()
        remaining = msg_repo.list_for_conversation(conversation.id)
        assert remaining == []


# =========================================================================== #
# Relationship integrity                                                       #
# =========================================================================== #


class TestRelationships:
    def test_user_conversations_relationship(
        self,
        db_session: Session,
        conv_repo: ConversationRepository,
        user: User,
    ) -> None:
        conv_repo.create(user_id=user.id, title="Conv A")
        conv_repo.create(user_id=user.id, title="Conv B")

        db_session.refresh(user)
        assert len(user.conversations) == 2

    def test_conversation_user_relationship(
        self,
        db_session: Session,
        conversation: Conversation,
        user: User,
    ) -> None:
        db_session.refresh(conversation)
        assert conversation.user.id == user.id

    def test_conversation_messages_relationship(
        self,
        db_session: Session,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hello",
        )
        db_session.refresh(conversation)
        assert len(conversation.messages) == 1

    def test_message_conversation_relationship(
        self,
        db_session: Session,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hi",
        )
        db_session.refresh(msg)
        assert msg.conversation.id == conversation.id


# =========================================================================== #
# Message model — citations property                                           #
# =========================================================================== #


class TestCitationsProperty:
    def test_citations_returns_empty_list_when_none(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="No citations",
        )
        assert msg.citations == []

    def test_citations_round_trip(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        data = [
            {"source": "doc.pdf", "page": 1},
            {"source": "other.pdf", "page": 5},
        ]
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Answer",
            citations=data,
        )
        assert msg.citations == data

    def test_citations_setter_clears_with_none(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Answer",
            citations=[{"source": "x.pdf"}],
        )
        msg.citations = None
        assert msg._citations is None
        assert msg.citations == []


# =========================================================================== #
# Message model — role_enum helper                                             #
# =========================================================================== #


class TestRoleEnumHelper:
    def test_role_enum_for_user(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Hi",
        )
        assert msg.role_enum is MessageRole.USER

    def test_role_enum_for_assistant(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Answer",
        )
        assert msg.role_enum is MessageRole.ASSISTANT

    def test_role_enum_returns_none_for_unknown_role(
        self,
        msg_repo: MessageRepository,
        conversation: Conversation,
    ) -> None:
        msg = msg_repo.create(
            conversation_id=conversation.id,
            role="future_role",
            content="From future",
        )
        assert msg.role_enum is None
