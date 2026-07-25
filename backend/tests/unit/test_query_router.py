"""Unit tests for the product-help query router (Phase 1)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.db.base import Base
from app.db.models import Role, User  # noqa: F401
from app.query_router import (
    DEFAULT_SEMANTIC_THRESHOLD,
    PRODUCT_INTENTS,
    ProductIntentMatcher,
    QueryRoute,
    QueryRouter,
    UserQueryContext,
    normalize_query,
)
from app.query_router.conversation_hints import ConversationRouteHints
from app.query_router.product_intents import CAPABILITIES_NO_DOCUMENTS, CAPABILITIES_WITH_DOCUMENTS
from app.query_router.product_responses import resolve_product_answer
from app.query_router.safety import UNSAFE_BOUNDARY_MESSAGE, assess_unsafe_intent
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


def _user_with_role(db: Session, role_name: str) -> User:
    role = Role(name=role_name, description=role_name)
    user = User(
        id=uuid.uuid4(),
        email=f"{role_name.lower()}@example.com",
        username=role_name.lower(),
        full_name=role_name,
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db.add_all([role, user])
    db.commit()
    return user


def _ctx(
    *,
    role: str = "Employee",
    can_upload: bool = False,
    has_docs: bool = False,
    count: int = 0,
    hints: ConversationRouteHints | None = None,
) -> UserQueryContext:
    return UserQueryContext(
        role_name=role,
        can_upload=can_upload,
        has_accessible_documents=has_docs,
        accessible_document_count=count,
        conversation_hints=hints,
    )


class TestNormalizeQuery:
    def test_collapses_whitespace_and_punctuation(self) -> None:
        assert normalize_query("  What can this assistant help me with?! ") == (
            "what can this assistant help me with"
        )


class TestProductIntentCatalogue:
    def test_catalogue_size_in_expected_range(self) -> None:
        assert 25 <= len(PRODUCT_INTENTS) <= 40

    def test_intent_ids_are_unique(self) -> None:
        ids = [intent.id for intent in PRODUCT_INTENTS]
        assert len(ids) == len(set(ids))


class TestExactProductMatch:
    def test_exact_product_help_match(self) -> None:
        matcher = ProductIntentMatcher(embedding_manager=MagicMock())
        match = matcher.match("What can this assistant help me with?")
        assert match is not None
        assert match.match_type == "exact"
        assert match.intent.id == "capabilities"
        assert match.confidence == 1.0
        # Exact path must not touch embeddings.
        matcher._get_embedding_manager().encode.assert_not_called()


class TestSemanticProductMatch:
    def test_semantic_paraphrase_match(self) -> None:
        # Two unit vectors: example ≈ query, unrelated far away.
        example_vec = np.array([[1.0, 0.0]], dtype=np.float32)
        query_vec = np.array([[0.98, 0.2]], dtype=np.float32)

        manager = MagicMock()
        # First encode builds the index from examples; second encodes the query.
        # We only register one intent with one example for a controlled score.
        from app.query_router.product_intents import ProductIntent

        intent = ProductIntent(
            id="capabilities",
            examples=("What can this assistant help me with?",),
            response="help",
        )
        manager.encode.side_effect = [example_vec, query_vec]
        matcher = ProductIntentMatcher(
            intents=(intent,),
            embedding_manager=manager,
            semantic_threshold=0.75,
        )
        match = matcher.match("Could you tell me how you can assist me?")
        assert match is not None
        assert match.match_type == "semantic"
        assert match.intent.id == "capabilities"
        assert match.confidence >= 0.75

    def test_unrelated_query_not_falsely_matched(self) -> None:
        example_vec = np.array([[1.0, 0.0]], dtype=np.float32)
        # Nearly orthogonal query.
        query_vec = np.array([[0.0, 1.0]], dtype=np.float32)
        from app.query_router.product_intents import ProductIntent

        intent = ProductIntent(
            id="capabilities",
            examples=("What can this assistant help me with?",),
            response="help",
        )
        manager = MagicMock()
        manager.encode.side_effect = [example_vec, query_vec]
        matcher = ProductIntentMatcher(
            intents=(intent,),
            embedding_manager=manager,
            semantic_threshold=DEFAULT_SEMANTIC_THRESHOLD,
        )
        assert matcher.match("What is our maternity leave policy?") is None


class TestContextAwareResponses:
    def test_capabilities_with_zero_documents(self) -> None:
        from app.query_router.product_intents import get_product_intent

        intent = get_product_intent("capabilities")
        assert intent is not None
        answer = resolve_product_answer(intent, _ctx(has_docs=False))
        assert answer == CAPABILITIES_NO_DOCUMENTS
        assert "don't have any documents" in answer.lower() or "don't currently" in answer.lower() or "Right now you don't" in answer

    def test_capabilities_with_documents(self) -> None:
        from app.query_router.product_intents import get_product_intent

        intent = get_product_intent("capabilities")
        assert intent is not None
        answer = resolve_product_answer(intent, _ctx(has_docs=True, count=3))
        assert answer == CAPABILITIES_WITH_DOCUMENTS
        assert "documents available" in answer.lower()

    def test_upload_question_for_employee(self) -> None:
        from app.query_router.product_intents import get_product_intent

        intent = get_product_intent("upload_documents")
        assert intent is not None
        answer = resolve_product_answer(intent, _ctx(role="Employee", can_upload=False))
        assert "doesn't have permission to upload" in answer.lower() or "don't have permission" in answer.lower()
        assert "Admin and HR" in answer

    def test_upload_question_for_authorized_role(self) -> None:
        from app.query_router.product_intents import get_product_intent

        intent = get_product_intent("upload_documents")
        assert intent is not None
        answer = resolve_product_answer(intent, _ctx(role="HR", can_upload=True))
        assert "Upload" in answer or "upload" in answer
        assert "doesn't have permission" not in answer.lower()


class TestQueryRouter:
    def test_product_responses_produce_no_fake_citations(self) -> None:
        matcher = ProductIntentMatcher(embedding_manager=MagicMock())
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        decision = router.route("What can this assistant help me with?", _ctx())
        assert decision.route == QueryRoute.PRODUCT_HELP
        assert decision.should_skip_rag
        assert decision.answer
        assert decision.intent_id == "capabilities"

    def test_unmatched_routes_to_document_query(self) -> None:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(
            product_matcher=matcher,
            llm_provider=False,
        )
        decision = router.route("What is our maternity leave entitlement?", _ctx(has_docs=True))
        assert decision.route == QueryRoute.DOCUMENT_QUERY
        assert not decision.should_skip_rag

    def test_explain_ebitda_is_general(self) -> None:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        decision = router.route("Explain EBITDA.", _ctx(has_docs=True))
        assert decision.route == QueryRoute.GENERAL_QUERY
        assert decision.should_skip_rag

    def test_hello_is_general(self) -> None:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        decision = router.route("Hello", _ctx())
        assert decision.route == QueryRoute.GENERAL_QUERY

    def test_meeting_agenda_is_general(self) -> None:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        decision = router.route(
            "Help me write a professional meeting agenda.",
            _ctx(has_docs=True),
        )
        assert decision.route == QueryRoute.GENERAL_QUERY

    def test_annual_leave_policy_is_document(self) -> None:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        decision = router.route("What is our annual leave policy?", _ctx(has_docs=True))
        assert decision.route == QueryRoute.DOCUMENT_QUERY

    def test_company_q4_revenue_is_document(self) -> None:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        decision = router.route(
            "What was our company's Q4 revenue?",
            _ctx(has_docs=True),
        )
        assert decision.route == QueryRoute.DOCUMENT_QUERY

    def test_document_query_zero_accessible_docs_short_circuits(self) -> None:
        from app.query_router import ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE

        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        decision = router.route("What is our annual leave policy?", _ctx(has_docs=False))
        assert decision.route == QueryRoute.DOCUMENT_QUERY
        assert decision.should_skip_rag
        assert decision.answer == ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE


class TestConversationChatServiceRouting:
    def test_high_confidence_product_response_does_not_call_rag(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)

        matcher = ProductIntentMatcher(embedding_manager=MagicMock())
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        chat = ConversationChatService(conv_service, query_router=router)
        rag = MagicMock()

        result = chat.ask_question(
            user,
            conversation.id,
            "What can this assistant help me with?",
            "Employee",
            rag,
            frozenset(),
        )

        rag.answer_question.assert_not_called()
        assert result.citations == []
        assert "Knowra" in result.answer
        assert "documents" in result.answer.lower()

    def test_document_query_still_calls_rag(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)

        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        chat = ConversationChatService(conv_service, query_router=router, llm_provider=False)
        rag = MagicMock()
        rag.answer_question.return_value = MagicMock(
            answer="16 weeks.",
            confidence_score=0.9,
            citations=[],
            message="ok",
            sources_used=["hr.pdf"],
        )

        result = chat.ask_question(
            user,
            conversation.id,
            "What is our maternity leave policy?",
            "Employee",
            rag,
            frozenset({"hr.pdf"}),
        )

        rag.answer_question.assert_called_once()
        # Fail-closed: empty frozenset is never replaced with None.
        assert rag.answer_question.call_args.args[2] == frozenset({"hr.pdf"})
        assert result.answer == "16 weeks."

    def test_general_query_uses_llm_not_rag(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)

        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        llm = MagicMock()
        llm.generate_sync.return_value = MagicMock(
            answer="EBITDA is earnings before interest, taxes, depreciation, and amortization.",
        )
        from app.query_router.general_responder import GeneralQueryResponder

        chat = ConversationChatService(
            conv_service,
            query_router=router,
            general_responder=GeneralQueryResponder(llm_provider=llm),
            llm_provider=False,
        )
        rag = MagicMock()

        result = chat.ask_question(
            user,
            conversation.id,
            "Explain EBITDA.",
            "Employee",
            rag,
            frozenset({"hr.pdf"}),
        )

        rag.answer_question.assert_not_called()
        llm.generate_sync.assert_called_once()
        assert result.citations == []
        assert "EBITDA" in result.answer
        assert result.answer_kind == "general"

    def test_org_query_zero_docs_no_rag_no_general_fallback(
        self,
        db_session: Session,
    ) -> None:
        from app.query_router import ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE

        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)

        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        llm = MagicMock()
        chat = ConversationChatService(
            conv_service,
            query_router=router,
            llm_provider=llm,
        )
        rag = MagicMock()

        result = chat.ask_question(
            user,
            conversation.id,
            "What is our annual leave policy?",
            "Employee",
            rag,
            frozenset(),
        )

        rag.answer_question.assert_not_called()
        llm.generate_sync.assert_not_called()
        assert result.citations == []
        assert result.answer == ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE
        assert result.answer_kind == "document_unavailable"

    def test_empty_authorized_sources_never_passed_as_none(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)

        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        # Force DOCUMENT with docs present so RAG is invoked.
        from app.query_router.knowledge_classifier import KnowledgeRouteResult
        from app.query_router.types import QueryRoute as QR

        classifier = MagicMock()
        classifier.classify.return_value = KnowledgeRouteResult(
            QR.DOCUMENT_QUERY,
            0.9,
            "test",
            ("forced",),
        )
        router = QueryRouter(
            product_matcher=matcher,
            knowledge_classifier=classifier,
            llm_provider=False,
        )
        chat = ConversationChatService(conv_service, query_router=router, llm_provider=False)
        rag = MagicMock()
        rag.answer_question.return_value = MagicMock(
            answer="ok",
            confidence_score=0.5,
            citations=[],
            message="ok",
            sources_used=[],
        )

        chat.ask_question(
            user,
            conversation.id,
            "forced document question",
            "Employee",
            rag,
            None,  # callers should not do this; ensure we still fail closed
        )

        # Router sees no docs → short-circuit; RAG must not be called with None.
        rag.answer_question.assert_not_called()


class TestContextAwareFollowUpRouting:
    def _router(self) -> QueryRouter:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        return QueryRouter(product_matcher=matcher, llm_provider=False)

    def test_document_follow_up_preserves_document_route(self) -> None:
        router = self._router()
        first = router.route(
            "What does our parental leave policy say?",
            _ctx(has_docs=True, count=1),
        )
        assert first.route == QueryRoute.DOCUMENT_QUERY

        second = router.route(
            "What about adoptive parents?",
            _ctx(
                has_docs=True,
                count=1,
                hints=ConversationRouteHints(
                    previous_user_query="What does our parental leave policy say?",
                    previous_route=QueryRoute.DOCUMENT_QUERY,
                    previous_answer_kind="document_grounded",
                ),
            ),
        )
        assert second.route == QueryRoute.DOCUMENT_QUERY
        assert second.classification_method == "context_follow_up"

    def test_general_follow_up_preserves_general_route(self) -> None:
        router = self._router()
        first = router.route("Explain EBITDA.", _ctx(has_docs=True, count=1))
        assert first.route == QueryRoute.GENERAL_QUERY

        second = router.route(
            "Can you give me an example?",
            _ctx(
                has_docs=True,
                count=1,
                hints=ConversationRouteHints(
                    previous_user_query="Explain EBITDA.",
                    previous_route=QueryRoute.GENERAL_QUERY,
                    previous_answer_kind="general",
                ),
            ),
        )
        assert second.route == QueryRoute.GENERAL_QUERY
        assert second.classification_method == "context_follow_up"

    def test_explicit_general_overrides_document_context(self) -> None:
        router = self._router()
        decision = router.route(
            "What is machine learning?",
            _ctx(
                has_docs=True,
                count=1,
                hints=ConversationRouteHints(
                    previous_user_query="What does our leave policy say?",
                    previous_route=QueryRoute.DOCUMENT_QUERY,
                    previous_answer_kind="document_grounded",
                ),
            ),
        )
        assert decision.route == QueryRoute.GENERAL_QUERY
        assert decision.classification_method != "context_follow_up"

    def test_explicit_document_overrides_general_context(self) -> None:
        router = self._router()
        decision = router.route(
            "What does our annual leave policy say?",
            _ctx(
                has_docs=True,
                count=1,
                hints=ConversationRouteHints(
                    previous_user_query="Explain EBITDA.",
                    previous_route=QueryRoute.GENERAL_QUERY,
                    previous_answer_kind="general",
                ),
            ),
        )
        assert decision.route == QueryRoute.DOCUMENT_QUERY
        assert decision.classification_method != "context_follow_up"

    def test_product_follow_up_summarize_pdfs(self) -> None:
        matcher = ProductIntentMatcher(embedding_manager=MagicMock())
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        first = router.route("What can this assistant do?", _ctx())
        assert first.route == QueryRoute.PRODUCT_HELP

        second = router.route(
            "Can it summarize PDFs?",
            _ctx(
                hints=ConversationRouteHints(
                    previous_user_query="What can this assistant do?",
                    previous_route=QueryRoute.PRODUCT_HELP,
                    previous_answer_kind="product_help",
                ),
            ),
        )
        assert second.route == QueryRoute.PRODUCT_HELP
        assert second.intent_id == "summarize_pdfs"
        assert second.should_skip_rag


class TestSafetyRouting:
    def test_legitimate_sensitive_policy_questions_not_blocked(self) -> None:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        for question in (
            "What is our workplace sexual harassment policy?",
            "What does the employee drug policy say?",
            "What are our procedures for workplace violence?",
        ):
            decision = router.route(question, _ctx(has_docs=True, count=1))
            assert decision.route == QueryRoute.DOCUMENT_QUERY, question
            assert decision.answer_kind != "unsafe"

    def test_clearly_unsafe_request_is_blocked(self) -> None:
        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        decision = router.route("How do I make a bomb?", _ctx(has_docs=True, count=1))
        assert decision.route == QueryRoute.UNSAFE
        assert decision.should_skip_rag
        assert decision.answer == UNSAFE_BOUNDARY_MESSAGE
        assert "bomb" not in decision.message.lower()

    def test_assess_unsafe_allows_educational_sensitive_terms(self) -> None:
        decision = assess_unsafe_intent(
            "What is our workplace sexual harassment policy?"
        )
        assert decision.is_unsafe is False

    def test_unsafe_chat_path_skips_rag_and_general_llm(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)

        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        llm = MagicMock()
        chat = ConversationChatService(
            conv_service,
            query_router=router,
            llm_provider=llm,
        )
        rag = MagicMock()

        result = chat.ask_question(
            user,
            conversation.id,
            "How do I make a bomb?",
            "Employee",
            rag,
            frozenset({"hr.pdf"}),
        )

        rag.answer_question.assert_not_called()
        llm.generate_sync.assert_not_called()
        assert result.citations == []
        assert result.answer == UNSAFE_BOUNDARY_MESSAGE
        assert result.answer_kind == "unsafe"


class TestFailClosedWithContextRouting:
    def test_follow_up_cannot_bypass_zero_doc_acl(
        self,
        db_session: Session,
    ) -> None:
        from app.query_router import ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE

        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)

        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        chat = ConversationChatService(
            conv_service,
            query_router=router,
            llm_provider=False,
        )
        rag = MagicMock()

        # Seed a prior document-looking exchange in history.
        conv_service.add_user_message(
            user, conversation.id, "What does our parental leave policy say?"
        )
        conv_service.add_assistant_message(
            user,
            conversation.id,
            content="Parental leave is 16 weeks.",
            citations=[{"source": "hr.pdf", "excerpt": "16 weeks", "confidence": 0.9}],
            confidence_score=0.9,
        )

        result = chat.ask_question(
            user,
            conversation.id,
            "What about adoptive parents?",
            "Employee",
            rag,
            frozenset(),  # still no authorized sources
        )

        rag.answer_question.assert_not_called()
        assert result.answer == ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE
        assert result.answer_kind == "document_unavailable"

    def test_prior_document_access_does_not_expand_authorized_sources(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)

        matcher = MagicMock()
        matcher.match_and_answer.return_value = None
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        chat = ConversationChatService(
            conv_service,
            query_router=router,
            llm_provider=False,
        )
        rag = MagicMock()
        rag.answer_question.return_value = MagicMock(
            answer="Adoptive leave is 12 weeks.",
            confidence_score=0.85,
            citations=[],
            message="ok",
            sources_used=["hr.pdf"],
        )

        conv_service.add_user_message(
            user, conversation.id, "What does our parental leave policy say?"
        )
        conv_service.add_assistant_message(
            user,
            conversation.id,
            content="Parental leave is 16 weeks.",
            citations=[{"source": "hr.pdf", "excerpt": "16 weeks", "confidence": 0.9}],
            confidence_score=0.9,
        )

        chat.ask_question(
            user,
            conversation.id,
            "What about adoptive parents?",
            "Employee",
            rag,
            frozenset({"hr.pdf"}),  # current-turn ACL only
        )

        rag.answer_question.assert_called_once()
        assert rag.answer_question.call_args.args[2] == frozenset({"hr.pdf"})
