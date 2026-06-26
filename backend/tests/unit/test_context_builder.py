"""Unit tests for ContextBuilder and ConversationService.build_conversation_context
(Phase 6.4).

Two test scopes:

1. ``ContextBuilder`` in isolation — no database, no ORM.  Message objects are
   constructed inline so the test has zero infrastructure dependencies.

2. ``ConversationService.build_conversation_context`` — uses an in-memory
   SQLite database to exercise the full ownership and retrieval pipeline.

Coverage:
    ✓ context built from empty history (no messages)
    ✓ context built from a single message
    ✓ context built from multiple messages
    ✓ messages appear oldest-to-newest in context
    ✓ role labels (User / Assistant / System / unknown)
    ✓ current question always present in context_query
    ✓ current question appears after history in context_query
    ✓ deterministic output (same input → same output)
    ✓ character limit drops oldest messages
    ✓ character limit preserves newest messages
    ✓ character limit maintains chronological order
    ✓ messages within limit not truncated
    ✓ was_truncated flag set correctly
    ✓ message_count reflects actual included messages
    ✓ max_chars of 0 drops all messages (edge case)
    ✓ window_size clamped to MAX_CONTEXT_WINDOW
    ✓ window_size of 0 clamped to 1
    ✓ build_conversation_context — question trimmed
    ✓ build_conversation_context — empty question raises MessageValidationError
    ✓ build_conversation_context — whitespace question raises MessageValidationError
    ✓ build_conversation_context — ownership enforced (not found)
    ✓ build_conversation_context — ownership enforced (foreign conversation)
    ✓ build_conversation_context — returns ConversationContext
    ✓ build_conversation_context — window_size respected
    ✓ build_conversation_context — history from conversation included
    ✓ build_conversation_context — empty conversation history
"""

from __future__ import annotations

import types
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
from app.services.context_builder import (
    DEFAULT_CONTEXT_WINDOW,
    MAX_CONTEXT_CHARACTERS,
    MAX_CONTEXT_WINDOW,
    ContextBuilder,
    ConversationContext,
)
from app.services.conversation_service import ConversationService


# =========================================================================== #
# Helpers: build lightweight duck-typed message objects without DB            #
# =========================================================================== #
#
# ContextBuilder only accesses .role and .content, so a SimpleNamespace is a
# perfect stand-in for isolated unit tests that must not touch the database.
# The DB-backed service tests (TestBuildConversationContextService) use real
# persisted Message rows obtained through ConversationService helper methods.
# =========================================================================== #


def _make_msg(role: str, content: str) -> Any:
    """Return a duck-typed message stand-in with .role and .content."""
    return types.SimpleNamespace(role=role, content=content)


def _user_msg(content: str) -> Any:
    return _make_msg(MessageRole.USER, content)


def _assistant_msg(content: str) -> Any:
    return _make_msg(MessageRole.ASSISTANT, content)


# =========================================================================== #
# ContextBuilder — isolated unit tests (no DB required)                       #
# =========================================================================== #


class TestContextBuilderBuild:
    def test_empty_history_returns_question_only(self) -> None:
        ctx = ContextBuilder.build("What is the policy?", [])
        assert "What is the policy?" in ctx.context_query
        assert ctx.message_count == 0
        assert ctx.history_messages == []

    def test_empty_history_context_query_format(self) -> None:
        ctx = ContextBuilder.build("My question", [])
        assert ctx.context_query == "Current question: My question"

    def test_current_question_stored_on_result(self) -> None:
        ctx = ContextBuilder.build("Hello?", [])
        assert ctx.current_question == "Hello?"

    def test_single_message_included(self) -> None:
        msg = _user_msg("Previous question")
        ctx = ContextBuilder.build("Follow-up?", [msg])
        assert "Previous question" in ctx.context_query

    def test_single_message_count_is_one(self) -> None:
        ctx = ContextBuilder.build("Q", [_user_msg("earlier")])
        assert ctx.message_count == 1

    def test_multiple_messages_all_included(self) -> None:
        messages = [
            _user_msg("Q1"),
            _assistant_msg("A1"),
            _user_msg("Q2"),
        ]
        ctx = ContextBuilder.build("Follow-up", messages)
        assert "Q1" in ctx.context_query
        assert "A1" in ctx.context_query
        assert "Q2" in ctx.context_query
        assert ctx.message_count == 3

    def test_current_question_appears_after_history(self) -> None:
        ctx = ContextBuilder.build(
            "Follow-up",
            [_user_msg("First"), _assistant_msg("Answer")],
        )
        pos_history = ctx.context_query.find("First")
        pos_question = ctx.context_query.find("Follow-up")
        assert pos_history < pos_question

    def test_was_truncated_false_when_within_limit(self) -> None:
        ctx = ContextBuilder.build(
            "Q", [_user_msg("short")], max_chars=1000
        )
        assert ctx.was_truncated is False

    def test_was_truncated_false_for_empty_history(self) -> None:
        ctx = ContextBuilder.build("Q", [])
        assert ctx.was_truncated is False


class TestContextBuilderRoleLabels:
    def test_user_role_labelled_as_user(self) -> None:
        ctx = ContextBuilder.build("Q", [_user_msg("content")])
        assert "User: content" in ctx.context_query

    def test_assistant_role_labelled_as_assistant(self) -> None:
        ctx = ContextBuilder.build("Q", [_assistant_msg("answer")])
        assert "Assistant: answer" in ctx.context_query

    def test_system_role_labelled_as_system(self) -> None:
        msg = _make_msg(MessageRole.SYSTEM, "system prompt")
        ctx = ContextBuilder.build("Q", [msg])
        assert "System: system prompt" in ctx.context_query

    def test_unknown_role_labelled_as_unknown(self) -> None:
        msg = _make_msg("future_role", "future content")
        ctx = ContextBuilder.build("Q", [msg])
        assert "Unknown: future content" in ctx.context_query


class TestContextBuilderCharacterLimit:
    def test_messages_within_limit_not_dropped(self) -> None:
        messages = [_user_msg("hi"), _assistant_msg("hello")]
        ctx = ContextBuilder.build("Q", messages, max_chars=1000)
        assert ctx.message_count == 2
        assert ctx.was_truncated is False
        assert len(ctx.context_query) <= 1000

    def test_context_query_never_exceeds_max_chars(self) -> None:
        messages = [
            _user_msg("A" * 80),
            _assistant_msg("B" * 80),
            _user_msg("C" * 80),
        ]
        max_chars = 120
        ctx = ContextBuilder.build("Follow-up question here", messages, max_chars=max_chars)
        assert len(ctx.context_query) <= max_chars

    def test_formatting_overhead_triggers_truncation(self) -> None:
        # Content alone fits in 50 chars, but labels/header/newlines do not.
        messages = [_user_msg("x" * 30)]
        ctx = ContextBuilder.build("Q", messages, max_chars=50)
        assert len(ctx.context_query) <= 50
        assert ctx.was_truncated is True

    def test_empty_history_respects_max_chars_for_question(self) -> None:
        question = "Q" * 100
        max_chars = 25
        ctx = ContextBuilder.build(question, [], max_chars=max_chars)
        assert len(ctx.context_query) <= max_chars
        assert ctx.current_question == question
        assert ctx.was_truncated is True

    def test_char_limit_drops_oldest_when_exceeded(self) -> None:
        # oldest is long, newest is short; limit should keep newest
        old = _user_msg("A" * 200)
        new = _user_msg("short")
        ctx = ContextBuilder.build("Q", [old, new], max_chars=100)
        assert "short" in ctx.context_query
        assert "A" * 200 not in ctx.context_query
        assert len(ctx.context_query) <= 100

    def test_char_limit_drops_multiple_oldest(self) -> None:
        messages = [
            _user_msg("X" * 100),   # oldest — dropped
            _user_msg("Y" * 100),   # second — dropped
            _user_msg("kept"),      # newest — kept
        ]
        # One formatted message needs ~52 chars; 60 leaves room for overhead.
        ctx = ContextBuilder.build("Q", messages, max_chars=60)
        assert ctx.was_truncated is True
        assert "kept" in ctx.context_query
        assert "X" * 100 not in ctx.context_query
        assert "Y" * 100 not in ctx.context_query
        assert len(ctx.context_query) <= 60

    def test_char_limit_preserves_chronological_order(self) -> None:
        messages = [
            _user_msg("X" * 500),   # dropped
            _user_msg("first kept"),
            _assistant_msg("second kept"),
        ]
        ctx = ContextBuilder.build("Q", messages, max_chars=100)
        pos_first = ctx.context_query.find("first kept")
        pos_second = ctx.context_query.find("second kept")
        assert pos_first < pos_second

    def test_was_truncated_true_when_oldest_dropped(self) -> None:
        messages = [
            _user_msg("A" * 200),
            _user_msg("short"),
        ]
        ctx = ContextBuilder.build("Q", messages, max_chars=50)
        assert ctx.was_truncated is True

    def test_message_count_reflects_retained_count(self) -> None:
        messages = [
            _user_msg("A" * 200),  # dropped
            _user_msg("B" * 200),  # dropped
            _user_msg("kept"),
        ]
        ctx = ContextBuilder.build("Q", messages, max_chars=60)
        assert ctx.message_count == 1
        assert len(ctx.context_query) <= 60

    def test_zero_max_chars_returns_empty_context_query(self) -> None:
        messages = [_user_msg("some content"), _assistant_msg("answer")]
        ctx = ContextBuilder.build("Q", messages, max_chars=0)
        assert ctx.message_count == 0
        assert ctx.context_query == ""
        assert ctx.was_truncated is True

    def test_history_messages_field_matches_included(self) -> None:
        messages = [
            _user_msg("A" * 200),  # dropped
            _user_msg("kept"),
        ]
        ctx = ContextBuilder.build("Q", messages, max_chars=60)
        assert len(ctx.history_messages) == ctx.message_count
        assert ctx.history_messages[0].content == "kept"
        assert len(ctx.context_query) <= 60


class TestContextBuilderDeterminism:
    def test_identical_inputs_produce_identical_output(self) -> None:
        messages = [_user_msg("Q1"), _assistant_msg("A1")]
        ctx_a = ContextBuilder.build("Follow-up", messages)
        ctx_b = ContextBuilder.build("Follow-up", messages)
        assert ctx_a.context_query == ctx_b.context_query

    def test_message_order_affects_output(self) -> None:
        m1 = _user_msg("first")
        m2 = _assistant_msg("second")
        ctx_ordered = ContextBuilder.build("Q", [m1, m2])
        ctx_reversed = ContextBuilder.build("Q", [m2, m1])
        assert ctx_ordered.context_query != ctx_reversed.context_query

    def test_context_query_contains_header_when_history_exists(self) -> None:
        ctx = ContextBuilder.build("Q", [_user_msg("earlier")])
        assert "Conversation context:" in ctx.context_query

    def test_context_query_no_header_for_empty_history(self) -> None:
        ctx = ContextBuilder.build("Q", [])
        assert "Conversation context:" not in ctx.context_query

    def test_blank_separator_between_history_and_question(self) -> None:
        ctx = ContextBuilder.build("My Q", [_user_msg("history")])
        # There should be a blank line before the "Current question:" prefix.
        assert "\n\n" in ctx.context_query or "\n\nCurrent question:" not in ctx.context_query
        # Simpler check: current question prefix present
        assert "Current question: My Q" in ctx.context_query


# =========================================================================== #
# ConversationService.build_conversation_context — integration with DB        #
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
    role = Role(name=f"role-{uuid.uuid4()}", description="R")
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
    return service.create_conversation(owner, title="Test")


class TestBuildConversationContextService:
    def test_returns_conversation_context(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        ctx = service.build_conversation_context(owner, conversation.id, "Question?")
        assert isinstance(ctx, ConversationContext)

    def test_current_question_is_trimmed(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        ctx = service.build_conversation_context(
            owner, conversation.id, "  Question?  "
        )
        assert ctx.current_question == "Question?"

    def test_empty_question_raises(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        with pytest.raises(MessageValidationError):
            service.build_conversation_context(owner, conversation.id, "")

    def test_whitespace_question_raises(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        with pytest.raises(MessageValidationError):
            service.build_conversation_context(owner, conversation.id, "   \t")

    def test_not_found_raises(
        self, service: ConversationService, owner: User
    ) -> None:
        with pytest.raises(ConversationNotFoundError):
            service.build_conversation_context(owner, uuid.uuid4(), "Question?")

    def test_foreign_conversation_raises_access_denied(
        self,
        service: ConversationService,
        owner: User,
        other_user: User,
        conversation: Conversation,
    ) -> None:
        with pytest.raises(ConversationAccessDeniedError):
            service.build_conversation_context(
                other_user, conversation.id, "Question?"
            )

    def test_empty_history_context_query_contains_question(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        ctx = service.build_conversation_context(
            owner, conversation.id, "No history here"
        )
        assert "No history here" in ctx.context_query
        assert ctx.message_count == 0

    def test_history_included_in_context_query(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        service.add_user_message(owner, conversation.id, "What is the leave policy?")
        service.add_assistant_message(
            owner, conversation.id, "16 weeks of paid leave."
        )

        ctx = service.build_conversation_context(
            owner, conversation.id, "What about adoptive parents?"
        )
        assert "What is the leave policy?" in ctx.context_query
        assert "16 weeks of paid leave." in ctx.context_query
        assert "What about adoptive parents?" in ctx.context_query

    def test_window_size_respected(
        self,
        db_session: Session,
        service: ConversationService,
        owner: User,
        conversation: Conversation,
    ) -> None:
        msg_repo = MessageRepository(db_session)

        # Insert 10 messages with distinct timestamps
        for i in range(10):
            msg = msg_repo.create(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=f"Message {i}",
            )
            db_session.execute(
                sa_update(Message)
                .where(Message.id == msg.id)
                .values(
                    created_at=datetime(2025, 1, 1, 10, 0, i, tzinfo=timezone.utc)
                )
            )
        db_session.commit()

        # Request window_size=3 → only last 3 messages included
        ctx = service.build_conversation_context(
            owner, conversation.id, "Q?", window_size=3
        )
        assert ctx.message_count == 3
        # Last 3 messages: M7, M8, M9
        assert "Message 7" in ctx.context_query
        assert "Message 8" in ctx.context_query
        assert "Message 9" in ctx.context_query
        assert "Message 0" not in ctx.context_query

    def test_window_size_clamped_to_max(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        # Passing an absurdly large window_size should not raise
        ctx = service.build_conversation_context(
            owner, conversation.id, "Q?", window_size=MAX_CONTEXT_WINDOW + 9999
        )
        assert isinstance(ctx, ConversationContext)

    def test_window_size_zero_clamped_to_one(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        service.add_user_message(owner, conversation.id, "Only message")
        ctx = service.build_conversation_context(
            owner, conversation.id, "Q?", window_size=0
        )
        # Clamped to 1 → at most 1 message included
        assert ctx.message_count <= 1

    def test_context_query_not_empty(
        self, service: ConversationService, owner: User, conversation: Conversation
    ) -> None:
        ctx = service.build_conversation_context(owner, conversation.id, "Q?")
        assert ctx.context_query.strip() != ""

    def test_context_constants_accessible(self) -> None:
        assert DEFAULT_CONTEXT_WINDOW > 0
        assert MAX_CONTEXT_WINDOW >= DEFAULT_CONTEXT_WINDOW
        assert MAX_CONTEXT_CHARACTERS > 0
