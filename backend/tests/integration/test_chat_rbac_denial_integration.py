"""Integration test for RBAC-denied RAG chat persistence (RC1 regression guard).

Verifies the full HTTP path when category-level RBAC denies retrieval:
Employee asks a finance-routed question → EnterpriseRAG returns an empty
``answer`` with an access-denied ``message`` → ConversationChatService
resolves persistable content → ConversationService validation succeeds.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import MessageRole, User
from app.db.repositories.message_repository import MessageRepository
from app.dependencies import get_db, get_rag_service_dep
from app.main import app
from app.rag.engine import EnterpriseRAG
from app.rag.rbac import check_access, validate_role
from app.rag.router import route_query
from app.services.rag_service import RagService
from tests.integration.chat_helpers import ASK_URL, ask_payload, create_conversation
from tests.integration.conftest import access_token_for, bearer_headers

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "sample_docs"
FINANCE_QUESTION = "What is the expense reimbursement process?"


def _build_rbac_denial_rag_service() -> RagService:
    """Return RagService whose engine performs real RBAC before retrieval."""
    from app.config import get_settings

    service = RagService(get_settings())
    engine = EnterpriseRAG(data_dir=FIXTURES_DIR)
    engine._initialized = True
    service._engine = engine
    service._initialized = True
    service._chunk_count = 0
    return service


@pytest.fixture
def rbac_denial_rag_service() -> RagService:
    return _build_rbac_denial_rag_service()


@pytest.fixture
def rbac_chat_client(
    db_session: Session,
    rbac_denial_rag_service: RagService,
) -> Generator[TestClient, None, None]:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rag_service_dep] = lambda: rbac_denial_rag_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestChatRbacDenialIntegration:
    def test_employee_finance_question_persists_access_denied_assistant_message(
        self,
        rbac_chat_client: TestClient,
        rbac_denial_rag_service: RagService,
        active_user: User,
        db_session: Session,
    ) -> None:
        """End-to-end guard against empty assistant content on RBAC denial."""
        from tests.integration.chat_helpers import add_public_searchable_document

        # Ensure DOCUMENT_QUERY reaches RAG (zero accessible docs short-circuits
        # before category RBAC). Category denial still applies on the finance route.
        add_public_searchable_document(db_session, active_user)

        role_name = active_user.roles[0].name
        route = route_query(FINANCE_QUESTION)
        access = check_access(validate_role(role_name), route.category)
        assert access.allowed is False

        engine_response = rbac_denial_rag_service.answer_question(
            FINANCE_QUESTION,
            role_name,
            frozenset({"integration_public.txt"}),
        )
        assert engine_response.answer == ""
        assert engine_response.message.strip()
        assert "Access denied" in engine_response.message

        token = access_token_for(active_user)
        conversation_id = create_conversation(
            rbac_chat_client,
            token,
            title="Expense policy",
        )

        response = rbac_chat_client.post(
            ASK_URL,
            headers=bearer_headers(token),
            json=ask_payload(conversation_id, FINANCE_QUESTION),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        assert data["answer"].strip()
        assert data["answer"] == engine_response.message
        assert "Access denied" in data["answer"]
        assert data["citations"] == []
        assert data["confidence_score"] == 0.0

        messages = MessageRepository(db_session).list_for_conversation(
            uuid.UUID(conversation_id),
        )
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == FINANCE_QUESTION
        assert messages[1].role == MessageRole.ASSISTANT
        assert messages[1].content.strip()
        assert messages[1].content == data["answer"]
        assert messages[1].content == engine_response.message
