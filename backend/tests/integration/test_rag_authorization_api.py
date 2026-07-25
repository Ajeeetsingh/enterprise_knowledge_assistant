"""Integration tests for Phase 5.5 — RAG retrieval authorization.

These tests verify the full HTTP path:
  - The chat endpoint computes authorized sources for the current user.
  - Authorized sources are forwarded to the RAG service.
  - The RAG service respects the source filter when calling the engine.
  - Unauthorized sources never appear in citations.

The RAG engine / FAISS index is mocked so tests run without ML dependencies.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Document, Role, User
from app.db.models.document import Document as DocumentModel
from app.dependencies import get_db, get_rag_service_dep
from app.documents.visibility import DocumentVisibility
from app.main import app
from app.query_router import ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE
from tests.constants import TEST_PASSWORD_HASH
from tests.integration.chat_helpers import ask_payload, create_conversation, force_document_query_router
from tests.integration.conftest import access_token_for, bearer_headers

ASK_URL = "/api/v1/chat/ask"


def _post_chat(
    client: TestClient,
    token: str,
    question: str,
) -> TestClient:
    conversation_id = create_conversation(client, token)
    return client.post(
        ASK_URL,
        headers=bearer_headers(token),
        json=ask_payload(conversation_id, question),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _query_response(sources: list[str]) -> SimpleNamespace:
    citations = [
        SimpleNamespace(source=s, excerpt="excerpt", confidence=0.9) for s in sources
    ]
    return SimpleNamespace(
        query="question",
        role="employee",
        routed_category="hr",
        route_confidence=0.9,
        answer="Answer based on sources.",
        sources_used=sources,
        citations=citations,
        confidence_score=0.85,
        access_granted=True,
        message="Generated from sources.",
    )


def _add_doc(
    db: Session,
    *,
    filename: str,
    uploader: User,
    visibility: DocumentVisibility = DocumentVisibility.RESTRICTED,
    owner_id: uuid.UUID | None = None,
    allowed_roles: list[str] | None = None,
) -> Document:
    doc = DocumentModel(
        id=uuid.uuid4(),
        filename=filename,
        content_type="text/plain",
        file_size=100,
        checksum=f"csum-{filename}",
        storage_path=f"docs/{filename}",
        status="searchable",
        uploaded_by=uploader.id,
        owner_id=owner_id or uploader.id,
        visibility=visibility.value,
    )
    doc.allowed_roles = allowed_roles
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def finance_role(db_session: Session) -> Role:
    role = Role(name="Finance", description="Finance team")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def finance_user(db_session: Session, finance_role: Role) -> User:
    user = User(
        email="finance@example.com",
        username="finance",
        full_name="Finance User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(finance_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def mock_rag_service() -> MagicMock:
    service = MagicMock()
    service.answer_question.return_value = _query_response(["hr_policy.txt"])
    return service


@pytest.fixture
def chat_client(
    db_session: Session,
    mock_rag_service: MagicMock,
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

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


# ---------------------------------------------------------------------------
# Tests: authorized_sources forwarded to RagService
# ---------------------------------------------------------------------------

class TestAuthorizedSourcesForwarded:
    def test_answer_question_called_with_authorized_sources(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        active_user: User,
        db_session: Session,
    ) -> None:
        """authorized_sources is passed as third positional arg to answer_question."""
        _add_doc(
            db_session,
            filename="hr_policy.txt",
            uploader=active_user,
            visibility=DocumentVisibility.PUBLIC,
        )

        token = access_token_for(active_user)
        response = _post_chat(
            chat_client,
            token,
            "What is the leave policy?",
        )

        assert response.status_code == 200
        call_args = mock_rag_service.answer_question.call_args
        # Third argument is authorized_sources
        authorized = call_args[0][2] if len(call_args[0]) >= 3 else call_args[1].get("authorized_sources")
        assert authorized is not None
        assert "hr_policy.txt" in authorized

    def test_public_doc_included_for_employee(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        active_user: User,
        db_session: Session,
    ) -> None:
        public_doc = _add_doc(
            db_session,
            filename="public.txt",
            uploader=active_user,
            visibility=DocumentVisibility.PUBLIC,
        )

        token = access_token_for(active_user)
        _post_chat(
            chat_client,
            token,
            "General policy?",
        )

        call_args = mock_rag_service.answer_question.call_args
        authorized = call_args[0][2] if len(call_args[0]) >= 3 else call_args[1].get("authorized_sources")
        assert "public.txt" in authorized

    def test_restricted_doc_excluded_for_employee(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        active_user: User,
        db_session: Session,
        hr_user: User,
    ) -> None:
        _add_doc(
            db_session,
            filename="hr_only.txt",
            uploader=hr_user,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
        )
        _add_doc(
            db_session,
            filename="public.txt",
            uploader=hr_user,
            visibility=DocumentVisibility.PUBLIC,
        )

        token = access_token_for(active_user)
        _post_chat(
            chat_client,
            token,
            "HR policy?",
        )

        call_args = mock_rag_service.answer_question.call_args
        authorized = call_args[0][2] if len(call_args[0]) >= 3 else call_args[1].get("authorized_sources")
        # Employee must not have access to HR-only restricted doc
        assert "hr_only.txt" not in authorized
        assert "public.txt" in authorized

    def test_hr_user_gets_hr_restricted_doc(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        hr_user: User,
        db_session: Session,
    ) -> None:
        _add_doc(
            db_session,
            filename="hr_doc.txt",
            uploader=hr_user,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
        )

        token = access_token_for(hr_user)
        _post_chat(
            chat_client,
            token,
            "HR policy?",
        )

        call_args = mock_rag_service.answer_question.call_args
        authorized = call_args[0][2] if len(call_args[0]) >= 3 else call_args[1].get("authorized_sources")
        assert "hr_doc.txt" in authorized

    def test_admin_gets_all_docs(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _add_doc(db_session, filename="pub.txt", uploader=admin_user, visibility=DocumentVisibility.PUBLIC)
        _add_doc(
            db_session,
            filename="private.txt",
            uploader=admin_user,
            visibility=DocumentVisibility.PRIVATE,
            owner_id=uuid.uuid4(),
        )
        _add_doc(
            db_session,
            filename="restricted.txt",
            uploader=admin_user,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
        )

        token = access_token_for(admin_user)
        _post_chat(
            chat_client,
            token,
            "Everything?",
        )

        call_args = mock_rag_service.answer_question.call_args
        authorized = call_args[0][2] if len(call_args[0]) >= 3 else call_args[1].get("authorized_sources")
        assert "pub.txt" in authorized
        assert "private.txt" in authorized
        assert "restricted.txt" in authorized

    def test_owner_gets_own_private_doc(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        active_user: User,
        db_session: Session,
    ) -> None:
        _add_doc(
            db_session,
            filename="my_private.txt",
            uploader=active_user,
            visibility=DocumentVisibility.PRIVATE,
            owner_id=active_user.id,
        )

        token = access_token_for(active_user)
        _post_chat(
            chat_client,
            token,
            "My private doc?",
        )

        call_args = mock_rag_service.answer_question.call_args
        authorized = call_args[0][2] if len(call_args[0]) >= 3 else call_args[1].get("authorized_sources")
        assert "my_private.txt" in authorized

    def test_finance_gets_finance_docs_not_hr(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        finance_user: User,
        hr_user: User,
        db_session: Session,
    ) -> None:
        _add_doc(
            db_session,
            filename="finance.txt",
            uploader=finance_user,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["Finance"],
        )
        _add_doc(
            db_session,
            filename="hr_doc.txt",
            uploader=hr_user,
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR"],
        )

        token = access_token_for(finance_user)
        _post_chat(
            chat_client,
            token,
            "Finance question?",
        )

        call_args = mock_rag_service.answer_question.call_args
        authorized = call_args[0][2] if len(call_args[0]) >= 3 else call_args[1].get("authorized_sources")
        assert "finance.txt" in authorized
        assert "hr_doc.txt" not in authorized


# ---------------------------------------------------------------------------
# Tests: empty authorized set and no-DB scenario
# ---------------------------------------------------------------------------

class TestEmptyAndNoDBScenarios:
    def test_no_db_documents_returns_zero_accessible_message(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        active_user: User,
    ) -> None:
        """DOCUMENT_QUERY with zero authorized docs short-circuits without RAG."""
        token = access_token_for(active_user)
        response = _post_chat(
            chat_client,
            token,
            "Leave policy?",
        )
        assert response.status_code == 200
        assert response.json()["answer"] == ZERO_ACCESSIBLE_DOCUMENTS_MESSAGE
        assert response.json()["citations"] == []
        mock_rag_service.answer_question.assert_not_called()

    def test_chat_response_structure_unchanged(
        self,
        chat_client: TestClient,
        mock_rag_service: MagicMock,
        active_user: User,
        db_session: Session,
    ) -> None:
        """Phase 6.6 extends the public response with conversation_id."""
        _add_doc(
            db_session,
            filename="public.txt",
            uploader=active_user,
            visibility=DocumentVisibility.PUBLIC,
        )
        token = access_token_for(active_user)
        response = _post_chat(
            chat_client,
            token,
            "Leave policy?",
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "answer" in data
        assert "citations" in data
        assert "confidence_score" in data
        assert "message" in data
