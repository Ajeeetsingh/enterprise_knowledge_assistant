"""Unit tests for ConversationChatService (Phase 6.6)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.core.exceptions import (
    ConversationAccessDeniedError,
    ConversationNotFoundError,
    RagRetrievalError,
)
from app.db.base import Base
from app.db.models import (  # noqa: F401
    Conversation,
    Document,
    Message,
    MessageRole,
    Role,
    User,
    user_roles,
)
from app.db.repositories.message_repository import MessageRepository
from app.rag.types import Citation
from app.services.conversation_chat_service import ConversationChatService
from app.services.conversation_service import build_conversation_service


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


@pytest.fixture
def owner(db_session: Session) -> User:
    role = Role(name=f"role-{uuid.uuid4()}", description="R")
    user = User(
        id=uuid.uuid4(),
        email="owner@example.com",
        username="owner",
        full_name="Owner",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    return user


@pytest.fixture
def other_user(db_session: Session) -> User:
    role = Role(name=f"role-{uuid.uuid4()}", description="R")
    user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        username="other",
        full_name="Other",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    return user


@pytest.fixture
def chat_service(db_session: Session) -> ConversationChatService:
    return ConversationChatService(build_conversation_service(db_session))


@pytest.fixture
def conversation(chat_service: ConversationChatService, owner: User, db_session: Session):
    conv_service = build_conversation_service(db_session)
    return conv_service.create_conversation(owner, title="Leave policy")


def _rag_response(
    *,
    answer: str = "16 weeks of paid leave.",
    confidence: float = 0.91,
) -> SimpleNamespace:
    return SimpleNamespace(
        answer=answer,
        confidence_score=confidence,
        citations=[
            Citation(source="hr_policy.txt", excerpt="Maternity leave: 16 weeks.", confidence=0.9)
        ],
        message="Answer generated from hr_policy.txt.",
    )


class TestConversationChatServiceAsk:
    def test_persists_user_and_assistant_messages(
        self,
        chat_service: ConversationChatService,
        db_session: Session,
        owner: User,
        conversation,
    ) -> None:
        rag = MagicMock()
        rag.answer_question.return_value = _rag_response()

        result = chat_service.ask_question(
            owner,
            conversation.id,
            "What is our maternity leave policy?",
            "Employee",
            rag,
            frozenset({"hr_policy.txt"}),
        )

        msg_repo = MessageRepository(db_session)
        messages = msg_repo.list_for_conversation(conversation.id)
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "What is our maternity leave policy?"
        assert messages[1].role == MessageRole.ASSISTANT
        assert messages[1].content == "16 weeks of paid leave."
        assert messages[1].citations == [
            {
                "source": "hr_policy.txt",
                "excerpt": "Maternity leave: 16 weeks.",
                "confidence": 0.9,
            }
        ]
        assert messages[1].confidence_score == 0.91
        assert result.answer == "16 weeks of paid leave."
        assert result.conversation_id == conversation.id

    def test_passes_context_query_to_rag(
        self,
        chat_service: ConversationChatService,
        owner: User,
        conversation,
        db_session: Session,
    ) -> None:
        conv_service = build_conversation_service(db_session)
        conv_service.add_user_message(
            owner,
            conversation.id,
            "What is our maternity leave policy?",
        )
        conv_service.add_assistant_message(
            owner,
            conversation.id,
            "16 weeks of paid leave.",
        )

        rag = MagicMock()
        rag.answer_question.return_value = _rag_response(answer="Adoptive parents receive 12 weeks.")

        chat_service.ask_question(
            owner,
            conversation.id,
            "What about adoptive parents?",
            "Employee",
            rag,
            frozenset(),
        )

        context_query = rag.answer_question.call_args[0][0]
        assert "What is our maternity leave policy?" in context_query
        assert "16 weeks of paid leave." in context_query
        assert context_query.endswith("Current question: What about adoptive parents?")
        history_section = context_query.split("\n\nCurrent question:")[0]
        assert "What about adoptive parents?" not in history_section

    def test_rag_failure_leaves_user_message_without_assistant(
        self,
        chat_service: ConversationChatService,
        db_session: Session,
        owner: User,
        conversation,
    ) -> None:
        rag = MagicMock()
        rag.answer_question.side_effect = RagRetrievalError("Knowledge retrieval failed.")

        with pytest.raises(RagRetrievalError):
            chat_service.ask_question(
                owner,
                conversation.id,
                "What is our maternity leave policy?",
                "Employee",
                rag,
                None,
            )

        messages = MessageRepository(db_session).list_for_conversation(conversation.id)
        assert len(messages) == 1
        assert messages[0].role == MessageRole.USER

    def test_conversation_not_found_raises(
        self,
        chat_service: ConversationChatService,
        owner: User,
    ) -> None:
        rag = MagicMock()
        with pytest.raises(ConversationNotFoundError):
            chat_service.ask_question(
                owner,
                uuid.uuid4(),
                "Question?",
                "Employee",
                rag,
                None,
            )
        rag.answer_question.assert_not_called()

    def test_foreign_conversation_raises_access_denied(
        self,
        chat_service: ConversationChatService,
        owner: User,
        other_user: User,
        conversation,
    ) -> None:
        rag = MagicMock()
        with pytest.raises(ConversationAccessDeniedError):
            chat_service.ask_question(
                other_user,
                conversation.id,
                "Question?",
                "Employee",
                rag,
                None,
            )
        rag.answer_question.assert_not_called()

    def test_authorized_sources_forwarded_to_rag(
        self,
        chat_service: ConversationChatService,
        owner: User,
        conversation,
    ) -> None:
        rag = MagicMock()
        rag.answer_question.return_value = _rag_response()
        authorized = frozenset({"hr_policy.txt", "public.txt"})

        chat_service.ask_question(
            owner,
            conversation.id,
            "Question?",
            "Employee",
            rag,
            authorized,
        )

        assert rag.answer_question.call_args[0][2] == authorized
