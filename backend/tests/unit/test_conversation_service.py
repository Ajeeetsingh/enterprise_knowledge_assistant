"""Unit tests for ConversationService (Phase 6.2).

All tests use real in-memory SQLite repositories so that full ownership
enforcement and cascade-delete behaviour can be exercised end-to-end without
any mocking.

Coverage:
    ✓ create_conversation — happy path
    ✓ create_conversation — title trimming
    ✓ create_conversation — blank title treated as None
    ✓ create_conversation — title exactly at max length (valid)
    ✓ create_conversation — title exceeds max length (invalid)
    ✓ create_conversation — None title persisted as None
    ✓ create_conversation — ownership correctly assigned
    ✓ get_conversation — owned conversation returned
    ✓ get_conversation — not-found raises ConversationNotFoundError
    ✓ get_conversation — foreign conversation raises ConversationAccessDeniedError
    ✓ list_conversations — returns only owned conversations
    ✓ list_conversations — empty result for new user
    ✓ list_conversations — returns total count including pages outside limit
    ✓ list_conversations — limit clamped to MAX_LIST_LIMIT
    ✓ list_conversations — offset clamped to >= 0
    ✓ list_conversations — pagination (limit + offset)
    ✓ delete_conversation — owned conversation deleted
    ✓ delete_conversation — returns True on success
    ✓ delete_conversation — not-found raises ConversationNotFoundError
    ✓ delete_conversation — foreign conversation raises ConversationAccessDeniedError
    ✓ delete_conversation — cascade deletes messages
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.core.exceptions import (
    ConversationAccessDeniedError,
    ConversationNotFoundError,
    ConversationValidationError,
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
    MAX_LIST_LIMIT,
    MAX_TITLE_LENGTH,
    ConversationService,
)


# =========================================================================== #
# Infrastructure fixtures                                                      #
# =========================================================================== #


@pytest.fixture
def db_session() -> Session:
    """Fresh in-memory SQLite session for each test."""
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


def _make_user(db: Session, *, email: str = "user@example.com") -> User:
    """Persist and return a minimal User."""
    role = Role(name=f"Employee-{uuid.uuid4()}", description="Employee")
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


# =========================================================================== #
# create_conversation                                                          #
# =========================================================================== #


class TestCreateConversation:
    def test_returns_conversation(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="HR Policies")
        assert conv is not None
        assert isinstance(conv.id, uuid.UUID)

    def test_assigns_ownership(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner)
        assert conv.user_id == owner.id

    def test_persists_title(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="Finance Q3")
        assert conv.title == "Finance Q3"

    def test_none_title_persisted_as_none(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title=None)
        assert conv.title is None

    def test_title_whitespace_trimmed(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="  Leave Policy  ")
        assert conv.title == "Leave Policy"

    def test_blank_title_treated_as_none(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="   ")
        assert conv.title is None

    def test_title_at_max_length_is_valid(
        self, service: ConversationService, owner: User
    ) -> None:
        title = "A" * MAX_TITLE_LENGTH
        conv = service.create_conversation(owner, title=title)
        assert conv.title == title

    def test_title_exceeds_max_length_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        title = "A" * (MAX_TITLE_LENGTH + 1)
        with pytest.raises(ConversationValidationError):
            service.create_conversation(owner, title=title)

    def test_multiple_conversations_have_unique_ids(
        self, service: ConversationService, owner: User
    ) -> None:
        a = service.create_conversation(owner)
        b = service.create_conversation(owner)
        assert a.id != b.id


# =========================================================================== #
# get_conversation                                                             #
# =========================================================================== #


class TestGetConversation:
    def test_returns_owned_conversation(
        self, service: ConversationService, owner: User
    ) -> None:
        created = service.create_conversation(owner, title="Q&A")
        found = service.get_conversation(owner, created.id)
        assert found.id == created.id

    def test_not_found_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            service.get_conversation(owner, uuid.uuid4())

    def test_foreign_conversation_raises_access_denied(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
    ) -> None:
        conv = service.create_conversation(owner)
        with pytest.raises(ConversationAccessDeniedError):
            service.get_conversation(other_user, conv.id)

    def test_returned_conversation_matches_creation(
        self, service: ConversationService, owner: User
    ) -> None:
        created = service.create_conversation(owner, title="Finance")
        fetched = service.get_conversation(owner, created.id)
        assert fetched.title == "Finance"
        assert fetched.user_id == owner.id


# =========================================================================== #
# list_conversations                                                           #
# =========================================================================== #


class TestListConversations:
    def test_returns_owned_conversations_only(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
    ) -> None:
        service.create_conversation(owner, title="Mine")
        service.create_conversation(owner, title="Also Mine")
        service.create_conversation(other_user, title="Not Mine")

        results, total = service.list_conversations(owner)
        assert total == 2
        assert all(c.user_id == owner.id for c in results)

    def test_empty_result_for_new_user(
        self, service: ConversationService, other_user: User
    ) -> None:
        results, total = service.list_conversations(other_user)
        assert results == []
        assert total == 0

    def test_total_count_exceeds_page_size(
        self, service: ConversationService, owner: User
    ) -> None:
        for i in range(5):
            service.create_conversation(owner, title=f"Conv {i}")

        results, total = service.list_conversations(owner, limit=3)
        assert total == 5
        assert len(results) == 3

    def test_pagination_offset(
        self, service: ConversationService, owner: User
    ) -> None:
        for i in range(5):
            service.create_conversation(owner, title=f"Conv {i}")

        results, total = service.list_conversations(owner, limit=10, offset=3)
        assert total == 5
        assert len(results) == 2

    def test_limit_clamped_to_max(
        self, service: ConversationService, owner: User
    ) -> None:
        for _ in range(3):
            service.create_conversation(owner)

        # Even if caller asks for more than MAX_LIST_LIMIT, we cap at max.
        results, _ = service.list_conversations(owner, limit=MAX_LIST_LIMIT + 9999)
        assert len(results) == 3

    def test_negative_offset_clamped_to_zero(
        self, service: ConversationService, owner: User
    ) -> None:
        service.create_conversation(owner)
        results, total = service.list_conversations(owner, offset=-100)
        assert total == 1
        assert len(results) == 1

    def test_limit_of_one_returns_one(
        self, service: ConversationService, owner: User
    ) -> None:
        service.create_conversation(owner, title="A")
        service.create_conversation(owner, title="B")

        results, total = service.list_conversations(owner, limit=1)
        assert total == 2
        assert len(results) == 1


# =========================================================================== #
# delete_conversation                                                          #
# =========================================================================== #


class TestDeleteConversation:
    def test_delete_owned_returns_true(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner)
        result = service.delete_conversation(owner, conv.id)
        assert result is True

    def test_delete_removes_conversation(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner)
        service.delete_conversation(owner, conv.id)
        with pytest.raises(ConversationNotFoundError):
            service.get_conversation(owner, conv.id)

    def test_delete_not_found_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            service.delete_conversation(owner, uuid.uuid4())

    def test_delete_foreign_conversation_raises_access_denied(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
    ) -> None:
        conv = service.create_conversation(owner)
        with pytest.raises(ConversationAccessDeniedError):
            service.delete_conversation(other_user, conv.id)

    def test_delete_does_not_expose_foreign_conversations_to_other_users(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
    ) -> None:
        """Ensure the other user's list is not affected by the owner's delete."""
        owner_conv = service.create_conversation(owner)
        other_conv = service.create_conversation(other_user)

        service.delete_conversation(owner, owner_conv.id)

        remaining, total = service.list_conversations(other_user)
        assert total == 1
        assert remaining[0].id == other_conv.id


# =========================================================================== #
# Cascade delete — messages                                                    #
# =========================================================================== #


class TestCascadeDeleteViaService:
    def test_delete_conversation_cascades_to_messages(
        self,
        db_session: Session,
        service: ConversationService,
        owner: User,
    ) -> None:
        msg_repo = MessageRepository(db_session)
        conv = service.create_conversation(owner)

        msg_repo.create(
            conversation_id=conv.id,
            role=MessageRole.USER,
            content="First question",
        )
        msg_repo.create(
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT,
            content="First answer",
        )

        service.delete_conversation(owner, conv.id)

        remaining = msg_repo.list_for_conversation(conv.id)
        assert remaining == []


# =========================================================================== #
# rename_conversation (Phase 6.7)                                              #
# =========================================================================== #


class TestRenameConversation:
    def test_rename_owned_conversation(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="Old Title")
        updated = service.rename_conversation(owner, conv.id, "New Title")
        assert updated.title == "New Title"
        assert updated.id == conv.id

    def test_rename_persists_to_database(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="Before")
        service.rename_conversation(owner, conv.id, "After")
        fetched = service.get_conversation(owner, conv.id)
        assert fetched.title == "After"

    def test_rename_trims_whitespace(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="Old")
        updated = service.rename_conversation(owner, conv.id, "  Trimmed Title  ")
        assert updated.title == "Trimmed Title"

    def test_rename_not_found_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            service.rename_conversation(owner, uuid.uuid4(), "New Title")

    def test_rename_foreign_conversation_raises_access_denied(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
    ) -> None:
        conv = service.create_conversation(owner, title="Private")
        with pytest.raises(ConversationAccessDeniedError):
            service.rename_conversation(other_user, conv.id, "Stolen Title")

    def test_rename_blank_title_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="Valid")
        with pytest.raises(ConversationValidationError):
            service.rename_conversation(owner, conv.id, "   ")

    def test_rename_title_too_long_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="Valid")
        with pytest.raises(ConversationValidationError):
            service.rename_conversation(owner, conv.id, "X" * (MAX_TITLE_LENGTH + 1))

    def test_rename_title_at_max_length_accepted(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="Old")
        title = "Y" * MAX_TITLE_LENGTH
        updated = service.rename_conversation(owner, conv.id, title)
        assert updated.title == title


# =========================================================================== #
# Title validation edge cases                                                  #
# =========================================================================== #


class TestTitleNormalization:
    def test_leading_whitespace_stripped(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="\t  HR Questions")
        assert conv.title == "HR Questions"

    def test_trailing_whitespace_stripped(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="Finance Review \n")
        assert conv.title == "Finance Review"

    def test_internal_whitespace_preserved(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="  Hello   World  ")
        assert conv.title == "Hello   World"

    def test_only_whitespace_becomes_none(
        self, service: ConversationService, owner: User
    ) -> None:
        conv = service.create_conversation(owner, title="\t\n  ")
        assert conv.title is None

    def test_title_one_over_max_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationValidationError) as exc_info:
            service.create_conversation(owner, title="X" * (MAX_TITLE_LENGTH + 1))
        assert str(MAX_TITLE_LENGTH) in str(exc_info.value)

    def test_title_exactly_max_length_accepted(
        self, service: ConversationService, owner: User
    ) -> None:
        title = "Z" * MAX_TITLE_LENGTH
        conv = service.create_conversation(owner, title=title)
        assert len(conv.title) == MAX_TITLE_LENGTH


# =========================================================================== #
# Ownership isolation (cross-user scenarios)                                   #
# =========================================================================== #


class TestOwnershipIsolation:
    def test_two_users_can_each_have_conversations(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
    ) -> None:
        service.create_conversation(owner, title="Owner's")
        service.create_conversation(other_user, title="Other's")

        owner_list, owner_total = service.list_conversations(owner)
        other_list, other_total = service.list_conversations(other_user)

        assert owner_total == 1
        assert other_total == 1
        assert owner_list[0].title == "Owner's"
        assert other_list[0].title == "Other's"

    def test_get_returns_different_errors_for_missing_vs_foreign(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
    ) -> None:
        conv = service.create_conversation(owner)

        # Completely missing: NotFound
        with pytest.raises(ConversationNotFoundError):
            service.get_conversation(owner, uuid.uuid4())

        # Exists but belongs to another user: AccessDenied
        with pytest.raises(ConversationAccessDeniedError):
            service.get_conversation(other_user, conv.id)
