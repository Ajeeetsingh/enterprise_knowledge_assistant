"""Final routing regression matrix, multi-turn, safety, and threshold guards.

These tests aggressively exercise the Phase 1–3 query router the way a real
user would. They do not introduce new product features — only verify routing,
follow-up inheritance, safety allow/deny, and semantic threshold precision.
"""

from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.db.base import Base
from app.db.models import Role, User  # noqa: F401
from app.query_router import (
    DEFAULT_SEMANTIC_THRESHOLD,
    ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE,
    ProductIntentMatcher,
    QueryRoute,
    QueryRouter,
    UserQueryContext,
)
from app.query_router.conversation_hints import ConversationRouteHints
from app.query_router.safety import UNSAFE_BOUNDARY_MESSAGE, assess_unsafe_intent
from app.services.conversation_chat_service import ConversationChatService
from app.services.conversation_service import build_conversation_service
from app.services.suggested_questions import (
    ONBOARDING_QUESTIONS_BASE,
    SuggestedQuestionService,
)


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
        email=f"{role_name.lower()}-{uuid.uuid4().hex[:6]}@example.com",
        username=f"{role_name.lower()}-{uuid.uuid4().hex[:6]}",
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
    has_docs: bool = True,
    count: int = 1,
    hints: ConversationRouteHints | None = None,
) -> UserQueryContext:
    return UserQueryContext(
        role_name="Employee",
        can_upload=False,
        has_accessible_documents=has_docs,
        accessible_document_count=count,
        conversation_hints=hints,
    )


def _doc_router() -> QueryRouter:
    matcher = MagicMock()
    matcher.match_and_answer.return_value = None
    return QueryRouter(product_matcher=matcher, llm_provider=False)


def _product_router() -> QueryRouter:
    return QueryRouter(
        product_matcher=ProductIntentMatcher(embedding_manager=MagicMock()),
        llm_provider=False,
    )


# ---------------------------------------------------------------------------
# 1. Routing regression matrix
# ---------------------------------------------------------------------------


class TestProductHelpMatrix:
    @pytest.mark.parametrize(
        "question,intent_id",
        [
            ("What can this assistant help me with?", "capabilities"),
            ("What can you do?", "capabilities"),
            ("What can this bot do?", "capabilities"),
            ("how can u help me", "capabilities"),
            ("What are you capable of?", "capabilities"),
            ("Can you summarize PDFs?", "summarize_pdfs"),
            ("How are my documents protected?", "document_permissions"),
            ("Who can see my files?", "document_permissions"),
            ("How does document access work?", "document_permissions"),
        ],
    )
    def test_product_help_exact_and_catalogue_paraphrases(
        self,
        question: str,
        intent_id: str,
    ) -> None:
        decision = _product_router().route(question, _ctx(has_docs=False, count=0))
        assert decision.route == QueryRoute.PRODUCT_HELP
        assert decision.intent_id == intent_id
        assert decision.should_skip_rag
        assert decision.answer
        assert decision.answer_kind == "product_help"


class TestDocumentQueryMatrix:
    @pytest.mark.parametrize(
        "question",
        [
            "What is our leave policy?",
            "What does the company say about remote work?",
            "Summarize our employee handbook.",
            "What was our Q4 revenue?",
            "According to the finance report, what is our liquidity position?",
            "What does our parental leave policy say?",
        ],
    )
    def test_document_queries(self, question: str) -> None:
        decision = _doc_router().route(question, _ctx())
        assert decision.route == QueryRoute.DOCUMENT_QUERY
        assert not decision.should_skip_rag


class TestGeneralQueryMatrix:
    @pytest.mark.parametrize(
        "question",
        [
            "Explain EBITDA.",
            "What is machine learning?",
            "Help me write a meeting agenda.",
            "What is the difference between revenue and profit?",
            "Hello, how are you?",
            "Hello!",
        ],
    )
    def test_general_queries(self, question: str) -> None:
        decision = _doc_router().route(question, _ctx())
        assert decision.route == QueryRoute.GENERAL_QUERY
        assert decision.should_skip_rag


class TestAmbiguousQueryDefaults:
    @pytest.mark.parametrize(
        "question",
        [
            "What about employees?",
            "Tell me more.",
            "Can you explain that?",
            "What about the other one?",
            "Everything?",
        ],
    )
    def test_ambiguous_without_context_defaults_document_safe(
        self,
        question: str,
    ) -> None:
        decision = _doc_router().route(question, _ctx())
        # Safe default when no prior turn — never invent general org facts.
        assert decision.route == QueryRoute.DOCUMENT_QUERY

    def test_ambiguous_follow_up_inherits_general(self) -> None:
        hints = ConversationRouteHints(
            previous_user_query="Explain EBITDA.",
            previous_route=QueryRoute.GENERAL_QUERY,
            previous_answer_kind="general",
        )
        decision = _doc_router().route("Tell me more.", _ctx(hints=hints))
        assert decision.route == QueryRoute.GENERAL_QUERY
        assert decision.classification_method == "context_follow_up"

    def test_ambiguous_follow_up_inherits_document(self) -> None:
        hints = ConversationRouteHints(
            previous_user_query="What is our leave policy?",
            previous_route=QueryRoute.DOCUMENT_QUERY,
            previous_answer_kind="document_grounded",
        )
        decision = _doc_router().route("What about employees?", _ctx(hints=hints))
        assert decision.route == QueryRoute.DOCUMENT_QUERY
        assert decision.classification_method == "context_follow_up"


# ---------------------------------------------------------------------------
# 2. Multi-turn conversation sequences
# ---------------------------------------------------------------------------


class TestMultiTurnDocumentConversation:
    def test_parental_leave_follow_up_chain(self) -> None:
        router = _doc_router()
        turns = [
            ("What is our parental leave policy?", None, QueryRoute.DOCUMENT_QUERY),
            (
                "What about adoptive parents?",
                QueryRoute.DOCUMENT_QUERY,
                QueryRoute.DOCUMENT_QUERY,
            ),
            (
                "And contractors?",
                QueryRoute.DOCUMENT_QUERY,
                QueryRoute.DOCUMENT_QUERY,
            ),
            (
                "Summarize that for me.",
                QueryRoute.DOCUMENT_QUERY,
                QueryRoute.DOCUMENT_QUERY,
            ),
        ]
        prev: QueryRoute | None = None
        for question, expected_prev, expected_route in turns:
            hints = None
            if expected_prev is not None:
                hints = ConversationRouteHints(
                    previous_user_query="prior",
                    previous_route=expected_prev,
                    previous_answer_kind="document_grounded",
                )
            decision = router.route(question, _ctx(hints=hints))
            assert decision.route == expected_route, question
            prev = decision.route
        assert prev == QueryRoute.DOCUMENT_QUERY


class TestMultiTurnGeneralConversation:
    def test_ebitda_follow_up_chain(self) -> None:
        router = _doc_router()
        turns = [
            ("Explain EBITDA.", None, QueryRoute.GENERAL_QUERY),
            ("Give me an example.", QueryRoute.GENERAL_QUERY, QueryRoute.GENERAL_QUERY),
            ("Make it simpler.", QueryRoute.GENERAL_QUERY, QueryRoute.GENERAL_QUERY),
        ]
        for question, expected_prev, expected_route in turns:
            hints = None
            if expected_prev is not None:
                hints = ConversationRouteHints(
                    previous_user_query="prior",
                    previous_route=expected_prev,
                    previous_answer_kind="general",
                )
            decision = router.route(question, _ctx(hints=hints))
            assert decision.route == expected_route, question


class TestMultiTurnTopicSwitching:
    def test_document_to_general_to_document(self) -> None:
        router = _doc_router()
        sequence = [
            ("What is our parental leave policy?", None, QueryRoute.DOCUMENT_QUERY),
            (
                "What about adoptive parents?",
                QueryRoute.DOCUMENT_QUERY,
                QueryRoute.DOCUMENT_QUERY,
            ),
            (
                "What is machine learning?",
                QueryRoute.DOCUMENT_QUERY,
                QueryRoute.GENERAL_QUERY,
            ),
            (
                "Can you give me an example?",
                QueryRoute.GENERAL_QUERY,
                QueryRoute.GENERAL_QUERY,
            ),
            (
                "What does our annual leave policy say?",
                QueryRoute.GENERAL_QUERY,
                QueryRoute.DOCUMENT_QUERY,
            ),
        ]
        for question, expected_prev, expected_route in sequence:
            hints = None
            if expected_prev is not None:
                hints = ConversationRouteHints(
                    previous_user_query="prior",
                    previous_route=expected_prev,
                    previous_answer_kind=(
                        "general"
                        if expected_prev == QueryRoute.GENERAL_QUERY
                        else "document_grounded"
                    ),
                )
            decision = router.route(question, _ctx(hints=hints))
            assert decision.route == expected_route, question


# ---------------------------------------------------------------------------
# 3. Zero-document user
# ---------------------------------------------------------------------------


class TestZeroDocumentUser:
    def test_onboarding_suggestions_are_useful(self) -> None:
        class _EmptyStore:
            chunks: list = []

        service = SuggestedQuestionService(_EmptyStore())
        suggestions = service.get_suggestions(frozenset(), can_upload=False)
        texts = [item.text for item in suggestions]
        assert texts[0] == ONBOARDING_QUESTIONS_BASE[0]
        assert any("assistant help" in t.lower() for t in texts)
        assert not any("leave policy" in t.lower() for t in texts)

    def test_product_and_general_and_org_zero_doc_paths(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)
        router = QueryRouter(
            product_matcher=ProductIntentMatcher(embedding_manager=MagicMock()),
            llm_provider=False,
        )
        llm = MagicMock()
        llm.generate_sync.return_value = MagicMock(
            answer="EBITDA is earnings before interest, taxes, depreciation and amortization.",
        )
        from app.query_router.general_responder import GeneralQueryResponder

        chat = ConversationChatService(
            conv_service,
            query_router=router,
            general_responder=GeneralQueryResponder(llm_provider=llm),
            llm_provider=False,
        )
        rag = MagicMock()

        product = chat.ask_question(
            user,
            conversation.id,
            "What can this assistant help me with?",
            "Employee",
            rag,
            frozenset(),
        )
        assert product.citations == []
        assert "Knowra" in product.answer
        rag.answer_question.assert_not_called()

        general = chat.ask_question(
            user,
            conversation.id,
            "Explain EBITDA.",
            "Employee",
            rag,
            frozenset(),
        )
        assert general.citations == []
        assert "EBITDA" in general.answer
        rag.answer_question.assert_not_called()

        org = chat.ask_question(
            user,
            conversation.id,
            "What is our annual leave policy?",
            "Employee",
            rag,
            frozenset(),
        )
        assert org.answer == ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE
        assert org.citations == []
        rag.answer_question.assert_not_called()


# ---------------------------------------------------------------------------
# 4–5. Document-aware + RBAC fail-closed with context
# ---------------------------------------------------------------------------


class TestDocumentAwareAndRbac:
    def test_document_path_calls_rag_with_citations_path(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)
        chat = ConversationChatService(
            conv_service,
            query_router=_doc_router(),
            llm_provider=False,
        )
        rag = MagicMock()
        rag.answer_question.return_value = MagicMock(
            answer="Parental leave is 16 weeks.",
            confidence_score=0.9,
            citations=[
                MagicMock(source="hr.pdf", excerpt="16 weeks", confidence=0.9, page=3),
            ],
            message="ok",
            sources_used=["hr.pdf"],
        )
        result = chat.ask_question(
            user,
            conversation.id,
            "What is our parental leave policy?",
            "Employee",
            rag,
            frozenset({"hr.pdf"}),
        )
        rag.answer_question.assert_called_once()
        assert rag.answer_question.call_args.args[2] == frozenset({"hr.pdf"})
        assert result.citations
        assert result.citations[0]["source"] == "hr.pdf"

    def test_general_and_product_bypass_rag(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)
        router = QueryRouter(
            product_matcher=ProductIntentMatcher(embedding_manager=MagicMock()),
            llm_provider=False,
        )
        llm = MagicMock()
        llm.generate_sync.return_value = MagicMock(answer="Machine learning is…")
        from app.query_router.general_responder import GeneralQueryResponder

        chat = ConversationChatService(
            conv_service,
            query_router=router,
            general_responder=GeneralQueryResponder(llm_provider=llm),
            llm_provider=False,
        )
        rag = MagicMock()
        chat.ask_question(
            user,
            conversation.id,
            "What can you do?",
            "Employee",
            rag,
            frozenset({"hr.pdf"}),
        )
        chat.ask_question(
            user,
            conversation.id,
            "What is machine learning?",
            "Employee",
            rag,
            frozenset({"hr.pdf"}),
        )
        rag.answer_question.assert_not_called()

    def test_context_cannot_expand_authorized_sources(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)
        chat = ConversationChatService(
            conv_service,
            query_router=_doc_router(),
            llm_provider=False,
        )
        rag = MagicMock()
        rag.answer_question.return_value = MagicMock(
            answer="Public handbook excerpt.",
            confidence_score=0.5,
            citations=[],
            message="ok",
            sources_used=["public.txt"],
        )
        # Prior turn looked at a restricted doc in the *conversation text only*;
        # authorization still comes solely from the current authorized_sources set.
        conv_service.add_user_message(
            user, conversation.id, "What does our parental leave policy say?"
        )
        conv_service.add_assistant_message(
            user,
            conversation.id,
            content="Parental leave is described in hr.pdf.",
            citations=[{"source": "hr.pdf", "excerpt": "16 weeks", "confidence": 0.9}],
            confidence_score=0.9,
        )
        chat.ask_question(
            user,
            conversation.id,
            "What about adoptive parents?",
            "Employee",
            rag,
            frozenset({"public.txt"}),
        )
        rag.answer_question.assert_called_once()
        assert rag.answer_question.call_args.args[2] == frozenset({"public.txt"})
        assert "hr.pdf" not in rag.answer_question.call_args.args[2]
    @pytest.mark.parametrize("role_name", ["Admin", "HR", "Finance", "Employee"])
    def test_empty_sources_remain_deny_all_for_all_roles(
        self,
        db_session: Session,
        role_name: str,
    ) -> None:
        user = _user_with_role(db_session, role_name)
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)
        chat = ConversationChatService(
            conv_service,
            query_router=_doc_router(),
            llm_provider=False,
        )
        rag = MagicMock()
        result = chat.ask_question(
            user,
            conversation.id,
            "What is our leave policy?",
            role_name,
            rag,
            frozenset(),
        )
        rag.answer_question.assert_not_called()
        assert result.answer == ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE
        assert result.citations == []


# ---------------------------------------------------------------------------
# 6. Threshold precision guard (keeps 0.78 unless evidence says otherwise)
# ---------------------------------------------------------------------------


class TestProductThresholdPrecision:
    def test_default_threshold_is_078(self) -> None:
        assert DEFAULT_SEMANTIC_THRESHOLD == 0.78

    def test_unrelated_org_queries_do_not_match_product_semantically(self) -> None:
        """Precision guard: org questions must stay below threshold.

        Uses a live embedding index when available; skips if the model cannot
        load in this environment.
        """
        try:
            matcher = ProductIntentMatcher()
            # Warm the index once.
            matcher.match("What can this assistant help me with?")
        except Exception as exc:  # pragma: no cover - env-dependent
            pytest.skip(f"Embedding model unavailable: {exc}")

        must_not_match = [
            "What is our leave policy?",
            "What does the company say about remote work?",
            "Summarize our employee handbook.",
            "What was our Q4 revenue?",
            "Explain EBITDA.",
            "What is machine learning?",
            "What is our sexual harassment policy?",
            "Help me write a meeting agenda.",
        ]
        for question in must_not_match:
            assert matcher.match(question) is None, question


# ---------------------------------------------------------------------------
# 8. Safety regression
# ---------------------------------------------------------------------------


class TestSafetyRegression:
    @pytest.mark.parametrize(
        "question",
        [
            "What is our sexual harassment policy?",
            "What does our drug and alcohol policy say?",
            "What is the workplace violence reporting procedure?",
        ],
    )
    def test_legitimate_sensitive_policy_not_blocked(self, question: str) -> None:
        assert assess_unsafe_intent(question).is_unsafe is False
        decision = _doc_router().route(question, _ctx())
        assert decision.route == QueryRoute.DOCUMENT_QUERY

    def test_clearly_unsafe_blocked_no_rag(
        self,
        db_session: Session,
    ) -> None:
        user = _user_with_role(db_session, "Employee")
        conv_service = build_conversation_service(db_session)
        conversation = conv_service.create_conversation(user)
        llm = MagicMock()
        chat = ConversationChatService(
            conv_service,
            query_router=_doc_router(),
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
        assert result.answer == UNSAFE_BOUNDARY_MESSAGE
        assert result.citations == []


# ---------------------------------------------------------------------------
# 9. Lightweight routing performance smoke
# ---------------------------------------------------------------------------


class TestRoutingPerformanceSmoke:
    def test_exact_product_and_deterministic_routes_are_fast(self) -> None:
        product_router = _product_router()
        doc_router = _doc_router()

        start = time.perf_counter()
        for _ in range(50):
            product_router.route("What can you do?", _ctx(has_docs=False, count=0))
            doc_router.route("What is our leave policy?", _ctx())
            doc_router.route("Explain EBITDA.", _ctx())
        elapsed_ms = (time.perf_counter() - start) * 1000
        # 150 deterministic/exact classifications should stay well under 1s locally.
        assert elapsed_ms < 2000, f"routing too slow: {elapsed_ms:.1f}ms"
