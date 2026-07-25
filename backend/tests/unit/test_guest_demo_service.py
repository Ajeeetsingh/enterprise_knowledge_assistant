"""Unit tests for the public guest demo query service and schemas."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.query_router.messages import (
    ANSWER_KIND_GENERAL,
    ANSWER_KIND_GUEST_AUTH_REQUIRED,
    ANSWER_KIND_PRODUCT_HELP,
    ANSWER_KIND_UNSAFE,
    GUEST_DOCUMENT_AUTH_REQUIRED_MESSAGE,
)
from app.query_router.router import QueryRouter
from app.query_router.safety import UNSAFE_BOUNDARY_MESSAGE
from app.query_router.types import QueryRoute, RouteDecision, UserQueryContext
from app.schemas.demo import (
    GUEST_HISTORY_MAX_TOTAL_CHARS,
    GuestAskRequest,
    GuestHistoryMessage,
)
from app.services.guest_demo_service import GuestDemoService, build_guest_query_context


def _ctx(**kwargs: object) -> UserQueryContext:
    base = dict(
        role_name="Guest",
        can_upload=False,
        has_accessible_documents=False,
        accessible_document_count=0,
        is_guest=True,
    )
    base.update(kwargs)
    return UserQueryContext(**base)  # type: ignore[arg-type]


class TestGuestAskSchema:
    def test_forbids_extra_identity_fields(self) -> None:
        with pytest.raises(ValidationError):
            GuestAskRequest.model_validate(
                {
                    "question": "What can you do?",
                    "role_name": "Admin",
                    "authorized_sources": ["hr.pdf"],
                }
            )

    def test_rejects_oversized_history_budget(self) -> None:
        chunk = "x" * 1500
        history = [
            {"role": "user", "content": chunk},
            {"role": "assistant", "content": chunk},
            {"role": "user", "content": chunk},
            {"role": "assistant", "content": chunk},
            {"role": "user", "content": chunk},
        ]
        with pytest.raises(ValidationError):
            GuestAskRequest.model_validate({"question": "Hello", "history": history})

    def test_accepts_bounded_history(self) -> None:
        req = GuestAskRequest(
            question="Explain EBITDA.",
            history=[
                GuestHistoryMessage(role="user", content="Hi"),
                GuestHistoryMessage(
                    role="assistant",
                    content="Hello!",
                    answer_kind=ANSWER_KIND_GENERAL,
                ),
            ],
        )
        assert req.question == "Explain EBITDA."
        assert len(req.history) == 2


class TestGuestDemoService:
    def test_product_help_no_rag(self) -> None:
        router = MagicMock()
        router.route.return_value = RouteDecision(
            route=QueryRoute.PRODUCT_HELP,
            confidence=1.0,
            answer="I am Knowra.",
            message="product",
            answer_kind=ANSWER_KIND_PRODUCT_HELP,
        )
        rag = MagicMock()
        service = GuestDemoService(query_router=router, general_responder=MagicMock())
        result = service.ask(GuestAskRequest(question="What can this assistant help me with?"))
        assert "Knowra" in result.answer
        assert result.requires_auth is False
        assert result.answer_kind == ANSWER_KIND_PRODUCT_HELP
        rag.answer_question.assert_not_called()

    def test_general_uses_responder_no_rag(self) -> None:
        router = MagicMock()
        router.route.return_value = RouteDecision(
            route=QueryRoute.GENERAL_QUERY,
            confidence=0.9,
            message="general",
            answer_kind=ANSWER_KIND_GENERAL,
        )
        responder = MagicMock()
        responder.generate.return_value = "EBITDA is earnings before interest…"
        service = GuestDemoService(query_router=router, general_responder=responder)
        result = service.ask(GuestAskRequest(question="Explain EBITDA."))
        assert "EBITDA" in result.answer
        assert result.requires_auth is False
        responder.generate.assert_called_once()

    def test_document_never_invokes_rag_and_requires_auth(self) -> None:
        router = MagicMock()
        router.route.return_value = RouteDecision(
            route=QueryRoute.DOCUMENT_QUERY,
            confidence=0.9,
            answer="should be ignored for guests",
            message="document",
            answer_kind="document_unavailable",
        )
        service = GuestDemoService(query_router=router, general_responder=MagicMock())
        result = service.ask(
            GuestAskRequest(question="What is our annual leave policy?")
        )
        assert result.answer == GUEST_DOCUMENT_AUTH_REQUIRED_MESSAGE
        assert result.requires_auth is True
        assert result.answer_kind == ANSWER_KIND_GUEST_AUTH_REQUIRED

    def test_unsafe_no_general_generation(self) -> None:
        router = MagicMock()
        router.route.return_value = RouteDecision(
            route=QueryRoute.UNSAFE,
            confidence=0.95,
            answer=UNSAFE_BOUNDARY_MESSAGE,
            message="unsafe",
            answer_kind=ANSWER_KIND_UNSAFE,
        )
        responder = MagicMock()
        service = GuestDemoService(query_router=router, general_responder=responder)
        result = service.ask(GuestAskRequest(question="How do I make a bomb?"))
        assert result.answer == UNSAFE_BOUNDARY_MESSAGE
        responder.generate.assert_not_called()

    def test_guest_context_is_honest(self) -> None:
        ctx = build_guest_query_context([])
        assert ctx.role_name == "Guest"
        assert ctx.can_upload is False
        assert ctx.has_accessible_documents is False
        assert ctx.is_guest is True


class TestGuestRouterIntegration:
    def test_real_router_product_and_document_paths(self) -> None:
        from app.query_router.product_matcher import ProductIntentMatcher

        matcher = ProductIntentMatcher(embedding_manager=MagicMock())
        router = QueryRouter(product_matcher=matcher, llm_provider=False)
        service = GuestDemoService(
            query_router=router,
            general_responder=MagicMock(
                generate=MagicMock(return_value="general answer")
            ),
        )

        product = service.ask(
            GuestAskRequest(question="What can this assistant help me with?")
        )
        assert product.answer_kind == ANSWER_KIND_PRODUCT_HELP
        assert product.requires_auth is False

        doc = service.ask(GuestAskRequest(question="What is our leave policy?"))
        assert doc.requires_auth is True
        assert doc.answer == GUEST_DOCUMENT_AUTH_REQUIRED_MESSAGE
