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
from app.rag.answer_generator import UNAVAILABLE_MESSAGE
from app.rag.types import Citation
from app.query_router import QueryRouter, QueryRoute
from app.query_router.knowledge_classifier import KnowledgeRouteResult
from app.services.conversation_chat_service import (
    ConversationChatService,
    resolve_assistant_content,
)
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
    """Force DOCUMENT_QUERY so Phase 2 general routing does not divert RAG tests."""
    return _force_document_chat_service(db_session)


def _force_document_chat_service(
    db_session: Session,
    *,
    title_llm_provider: object | None = None,
) -> ConversationChatService:
    matcher = MagicMock()
    matcher.match_and_answer.return_value = None
    classifier = MagicMock()
    classifier.classify.return_value = KnowledgeRouteResult(
        QueryRoute.DOCUMENT_QUERY,
        0.95,
        "test_force_document",
        ("test",),
    )
    router = QueryRouter(
        product_matcher=matcher,
        knowledge_classifier=classifier,
        llm_provider=False,
    )
    return ConversationChatService(
        build_conversation_service(db_session),
        title_llm_provider=title_llm_provider,  # type: ignore[arg-type]
        query_router=router,
        llm_provider=False,
    )


@pytest.fixture
def conversation(chat_service: ConversationChatService, owner: User, db_session: Session):
    conv_service = build_conversation_service(db_session)
    return conv_service.create_conversation(owner, title="Leave policy")


def _rag_response(
    *,
    answer: str = "16 weeks of paid leave.",
    confidence: float = 0.91,
    message: str = "Answer generated from hr_policy.txt.",
    citations: list[Citation] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        answer=answer,
        confidence_score=confidence,
        citations=citations
        if citations is not None
        else [
            Citation(source="hr_policy.txt", excerpt="Maternity leave: 16 weeks.", confidence=0.9)
        ],
        message=message,
    )


class TestResolveAssistantContent:
    def test_uses_answer_when_present(self) -> None:
        response = _rag_response(answer="Direct answer.")

        assert resolve_assistant_content(response) == "Direct answer."

    def test_uses_message_when_answer_blank(self) -> None:
        response = _rag_response(
            answer="",
            message="Access denied: role 'employee' cannot access 'finance' documents.",
        )

        assert (
            resolve_assistant_content(response)
            == "Access denied: role 'employee' cannot access 'finance' documents."
        )

    def test_uses_message_when_answer_whitespace_only(self) -> None:
        response = _rag_response(answer="   ", message="No relevant documents found for this query.")

        assert resolve_assistant_content(response) == "No relevant documents found for this query."

    def test_falls_back_when_answer_and_message_blank(self) -> None:
        response = _rag_response(answer="", message="")

        assert resolve_assistant_content(response) == UNAVAILABLE_MESSAGE


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
                "page": None,
            }
        ]
        assert messages[1].confidence_score == 0.91
        assert result.answer == "16 weeks of paid leave."
        assert result.conversation_id == conversation.id

    def test_passes_current_question_and_history_to_rag(
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
            frozenset({"hr_policy.txt"}),
        )

        assert rag.answer_question.call_args[0][0] == "What about adoptive parents?"
        conversation_history = rag.answer_question.call_args[1]["conversation_history"]
        assert conversation_history is not None
        assert "What is our maternity leave policy?" in conversation_history
        assert "16 weeks of paid leave." in conversation_history
        assert "What about adoptive parents?" not in conversation_history

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
                frozenset({"hr_policy.txt"}),
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

    def test_persists_rbac_denial_message_when_answer_blank(
        self,
        chat_service: ConversationChatService,
        db_session: Session,
        owner: User,
        conversation,
    ) -> None:
        denial_message = (
            "Access denied: role 'employee' cannot access 'finance' documents."
        )
        rag = MagicMock()
        rag.answer_question.return_value = _rag_response(
            answer="",
            message=denial_message,
            confidence=0.0,
            citations=[],
        )

        result = chat_service.ask_question(
            owner,
            conversation.id,
            "What is the expense reimbursement process?",
            "Employee",
            rag,
            frozenset({"finance_report.txt"}),
        )

        messages = MessageRepository(db_session).list_for_conversation(conversation.id)
        assert messages[1].role == MessageRole.ASSISTANT
        assert messages[1].content == denial_message
        assert messages[1].citations == []
        assert messages[1].confidence_score == 0.0
        assert result.answer == denial_message

    def test_persists_fallback_when_rag_returns_blank_content(
        self,
        chat_service: ConversationChatService,
        db_session: Session,
        owner: User,
        conversation,
    ) -> None:
        rag = MagicMock()
        rag.answer_question.return_value = _rag_response(
            answer="   ",
            message="",
            confidence=0.0,
            citations=[],
        )

        result = chat_service.ask_question(
            owner,
            conversation.id,
            "What is the quantum computing roadmap?",
            "Employee",
            rag,
            frozenset({"knowledge.txt"}),
        )

        messages = MessageRepository(db_session).list_for_conversation(conversation.id)
        assert messages[1].content == UNAVAILABLE_MESSAGE
        assert result.answer == UNAVAILABLE_MESSAGE

    def test_first_message_generates_title_via_deterministic_fallback(
        self,
        db_session: Session,
        owner: User,
    ) -> None:
        """No LLM provider wired in ⇒ deterministic fallback runs, and the
        generated title is persisted after the first user message."""
        conv_service = build_conversation_service(db_session)
        chat_service = _force_document_chat_service(db_session)
        conv = conv_service.create_conversation(owner)
        assert conv.title is None

        rag = MagicMock()
        rag.answer_question.return_value = _rag_response()

        chat_service.ask_question(
            owner,
            conv.id,
            "What are the main types of commercial paper issuers?",
            "Employee",
            rag,
            frozenset({"issuers.txt"}),
        )

        updated = conv_service.get_conversation(owner, conv.id)
        assert updated.title == "Commercial Paper Issuers"

    def test_existing_title_is_never_overwritten(
        self,
        chat_service: ConversationChatService,
        db_session: Session,
        owner: User,
        conversation,
    ) -> None:
        """`conversation` fixture is created with title="Leave policy"."""
        rag = MagicMock()
        rag.answer_question.return_value = _rag_response()

        chat_service.ask_question(
            owner,
            conversation.id,
            "What is our maternity leave policy?",
            "Employee",
            rag,
            frozenset({"hr_policy.txt"}),
        )

        conv_service = build_conversation_service(db_session)
        updated = conv_service.get_conversation(owner, conversation.id)
        assert updated.title == "Leave policy"

    def test_title_generated_once_and_not_regenerated_on_second_message(
        self,
        db_session: Session,
        owner: User,
    ) -> None:
        conv_service = build_conversation_service(db_session)
        chat_service = _force_document_chat_service(db_session)
        conv = conv_service.create_conversation(owner)

        rag = MagicMock()
        rag.answer_question.return_value = _rag_response()

        chat_service.ask_question(
            owner, conv.id, "Explain Project Phoenix.", "Employee", rag, frozenset({"doc.txt"})
        )
        first_title = conv_service.get_conversation(owner, conv.id).title
        assert first_title == "Project Phoenix"

        chat_service.ask_question(
            owner, conv.id, "What about the budget?", "Employee", rag, frozenset({"doc.txt"})
        )
        second_title = conv_service.get_conversation(owner, conv.id).title
        assert second_title == "Project Phoenix"

    def test_title_generation_failure_does_not_break_chat_response(
        self,
        db_session: Session,
        owner: User,
    ) -> None:
        """A broken title provider must never surface as a chat failure."""
        conv_service = build_conversation_service(db_session)
        broken_provider = MagicMock()
        broken_provider.generate_sync.side_effect = RuntimeError("provider down")
        chat_service = _force_document_chat_service(
            db_session,
            title_llm_provider=broken_provider,
        )
        conv = conv_service.create_conversation(owner)

        rag = MagicMock()
        rag.answer_question.return_value = _rag_response()

        result = chat_service.ask_question(
            owner, conv.id, "Explain Project Phoenix.", "Employee", rag, frozenset({"doc.txt"})
        )

        assert result.answer == "16 weeks of paid leave."
        # Deterministic fallback still ran despite the LLM provider failing.
        updated = conv_service.get_conversation(owner, conv.id)
        assert updated.title == "Project Phoenix"

    def test_uses_injected_llm_provider_for_title(
        self,
        db_session: Session,
        owner: User,
    ) -> None:
        conv_service = build_conversation_service(db_session)
        llm_provider = MagicMock()
        llm_provider.generate_sync.return_value = SimpleNamespace(answer="Money Market Funds")
        chat_service = _force_document_chat_service(
            db_session,
            title_llm_provider=llm_provider,
        )
        conv = conv_service.create_conversation(owner)

        rag = MagicMock()
        rag.answer_question.return_value = _rag_response()

        chat_service.ask_question(
            owner,
            conv.id,
            "How do money market funds work?",
            "Employee",
            rag,
            frozenset({"mmf.txt"}),
        )

        llm_provider.generate_sync.assert_called_once()
        updated = conv_service.get_conversation(owner, conv.id)
        assert updated.title == "Money Market Funds"

    def test_persists_no_retrieval_answer_from_rag(
        self,
        chat_service: ConversationChatService,
        db_session: Session,
        owner: User,
        conversation,
    ) -> None:
        no_results_answer = "No relevant documents found for this query."
        rag = MagicMock()
        rag.answer_question.return_value = _rag_response(
            answer=no_results_answer,
            message="Search completed but no matching chunks were found.",
            confidence=0.0,
            citations=[],
        )

        result = chat_service.ask_question(
            owner,
            conversation.id,
            "What is the quantum computing roadmap?",
            "Employee",
            rag,
            frozenset({"knowledge.txt"}),
        )

        messages = MessageRepository(db_session).list_for_conversation(conversation.id)
        assert messages[1].content == no_results_answer
        assert result.answer == no_results_answer
