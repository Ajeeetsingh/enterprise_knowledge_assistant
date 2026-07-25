"""Integration tests for conversation-aware chat (Phase 6.6)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import MessageRole, User
from app.db.repositories.message_repository import MessageRepository
from app.dependencies import get_db, get_rag_service_dep
from app.main import app
from tests.constants import TEST_PASSWORD_HASH
from tests.integration.chat_helpers import (
    ASK_URL,
    CONVERSATIONS_URL,
    add_public_searchable_document,
    ask_payload,
    create_conversation,
    force_document_query_router,
)
from tests.integration.conftest import access_token_for, bearer_headers


def _fake_answer(*, answer: str, confidence: float = 0.9) -> SimpleNamespace:
    return SimpleNamespace(
        answer=answer,
        confidence_score=confidence,
        citations=[
            SimpleNamespace(
                source="hr_policy.txt",
                excerpt="Relevant excerpt.",
                confidence=0.88,
            )
        ],
        message=f"Answer generated: {answer}",
    )


@pytest.fixture
def mock_rag_service() -> MagicMock:
    service = MagicMock()
    service.answer_question.side_effect = [
        _fake_answer(answer="16 weeks of paid maternity leave."),
        _fake_answer(answer="Adoptive parents receive 12 weeks of paid leave."),
    ]
    return service


@pytest.fixture
def chat_client(
    db_session: Session,
    mock_rag_service: MagicMock,
    active_user: User,
) -> TestClient:
    def override_get_db():
        yield db_session

    add_public_searchable_document(db_session, active_user, filename="hr_policy.txt")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rag_service_dep] = lambda: mock_rag_service
    with (
        patch(
            "app.services.conversation_chat_service.get_query_router",
            return_value=force_document_query_router(),
        ),
        TestClient(app) as test_client,
    ):
        yield test_client
    app.dependency_overrides.clear()


class TestConversationAwareChatFlow:
    def test_follow_up_question_flow(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        active_user: User,
        db_session: Session,
    ) -> None:
        token = access_token_for(active_user)
        conversation_id = create_conversation(chat_client, token, title="Leave policy")

        first = chat_client.post(
            ASK_URL,
            headers=bearer_headers(token),
            json=ask_payload(conversation_id, "What is our maternity leave policy?"),
        )
        second = chat_client.post(
            ASK_URL,
            headers=bearer_headers(token),
            json=ask_payload(conversation_id, "What about adoptive parents?"),
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["conversation_id"] == conversation_id
        assert second.json()["conversation_id"] == conversation_id
        assert "16 weeks" in first.json()["answer"]
        assert "12 weeks" in second.json()["answer"]

        second_call = mock_rag_service.answer_question.call_args_list[1]
        assert second_call[0][0] == "What about adoptive parents?"
        conversation_history = second_call[1]["conversation_history"]
        assert conversation_history is not None
        assert "What is our maternity leave policy?" in conversation_history
        assert "16 weeks of paid maternity leave." in conversation_history
        assert "What about adoptive parents?" not in conversation_history
        assert "context_query" not in second.json()

        messages = MessageRepository(db_session).list_for_conversation(
            uuid.UUID(conversation_id)
        )
        assert len(messages) == 4
        assert messages[0].role == MessageRole.USER
        assert messages[1].role == MessageRole.ASSISTANT
        assert messages[2].role == MessageRole.USER
        assert messages[3].role == MessageRole.ASSISTANT
        assert messages[1].citations
        assert messages[1].confidence_score == 0.9
        assert messages[3].citations
        assert messages[3].confidence_score == 0.9

    def test_foreign_conversation_returns_403(
        self,
        chat_client: TestClient,
        active_user: User,
        employee_role,
        db_session: Session,
    ) -> None:
        other = User(
            email="foreign@example.com",
            username="foreign",
            full_name="Foreign",
            password_hash=TEST_PASSWORD_HASH,
            is_active=True,
        )
        other.roles.append(employee_role)
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)

        owner_token = access_token_for(active_user)
        foreign_token = access_token_for(other)
        conversation_id = create_conversation(chat_client, owner_token)

        response = chat_client.post(
            ASK_URL,
            headers=bearer_headers(foreign_token),
            json=ask_payload(conversation_id, "Question?"),
        )
        assert response.status_code == 403

    def test_missing_conversation_returns_404(
        self,
        chat_client: TestClient,
        active_user: User,
    ) -> None:
        token = access_token_for(active_user)
        response = chat_client.post(
            ASK_URL,
            headers=bearer_headers(token),
            json=ask_payload(str(uuid.uuid4()), "Question?"),
        )
        assert response.status_code == 404

    def test_messages_available_via_conversation_history_endpoint(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        active_user: User,
    ) -> None:
        token = access_token_for(active_user)
        conversation_id = create_conversation(chat_client, token)

        chat_client.post(
            ASK_URL,
            headers=bearer_headers(token),
            json=ask_payload(conversation_id, "What is our maternity leave policy?"),
        )

        history = chat_client.get(
            f"{CONVERSATIONS_URL}/{conversation_id}/messages",
            headers=bearer_headers(token),
        )
        assert history.status_code == 200
        items = history.json()["items"]
        assert len(items) == 2
        assert items[0]["role"] == "user"
        assert items[1]["role"] == "assistant"
