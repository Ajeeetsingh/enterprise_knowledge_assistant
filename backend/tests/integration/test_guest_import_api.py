"""Integration tests for POST /api/v1/conversations/import-guest."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from tests.integration.conftest import access_token_for, bearer_headers

IMPORT_URL = "/api/v1/conversations/import-guest"


class TestGuestImportApi:
    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.post(
            IMPORT_URL,
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )
        assert response.status_code == 401

    def test_imports_valid_guest_history(
        self, client: TestClient, active_user: User, db_session: Session
    ) -> None:
        token = access_token_for(active_user)
        response = client.post(
            IMPORT_URL,
            headers=bearer_headers(token),
            json={
                "messages": [
                    {"role": "user", "content": "What formats are supported?"},
                    {
                        "role": "assistant",
                        "content": "PDF, DOCX, and TXT are supported.",
                    },
                ]
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Guest conversation"
        conversation_id = uuid.UUID(data["id"])

        messages = list(
            db_session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            )
        )
        assert len(messages) == 2
        assert messages[0].content == "What formats are supported?"
        assert messages[1].citations == []
        assert messages[1].confidence_score is None

        history = client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=bearer_headers(token),
        )
        assert history.status_code == 200
        items = history.json()["items"]
        assert items[1]["citations"] == []
        assert items[1]["confidence_score"] is None

    def test_rejects_client_supplied_ids_and_citations(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.post(
            IMPORT_URL,
            headers=bearer_headers(token),
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "Hi",
                        "id": str(uuid.uuid4()),
                        "citations": [{"source": "secret.pdf"}],
                    }
                ]
            },
        )
        assert response.status_code == 422

    def test_rejects_authorized_sources_and_roles(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.post(
            IMPORT_URL,
            headers=bearer_headers(token),
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "authorized_sources": ["hr.pdf"],
                "role_name": "Admin",
                "permissions": ["documents:read"],
            },
        )
        assert response.status_code == 422

    def test_rejects_system_role(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.post(
            IMPORT_URL,
            headers=bearer_headers(token),
            json={"messages": [{"role": "system", "content": "Nope"}]},
        )
        assert response.status_code == 422

    def test_rejects_oversized_history(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        messages = [{"role": "user", "content": f"q{i}"} for i in range(25)]
        response = client.post(
            IMPORT_URL,
            headers=bearer_headers(token),
            json={"messages": messages},
        )
        assert response.status_code == 422

    def test_malformed_payload_creates_no_conversation(
        self, client: TestClient, active_user: User, db_session: Session
    ) -> None:
        token = access_token_for(active_user)
        before = list(
            db_session.scalars(
                select(Conversation).where(Conversation.user_id == active_user.id)
            )
        )
        response = client.post(
            IMPORT_URL,
            headers=bearer_headers(token),
            json={"messages": [{"role": "assistant", "content": ""}]},
        )
        assert response.status_code == 422
        after = list(
            db_session.scalars(
                select(Conversation).where(Conversation.user_id == active_user.id)
            )
        )
        assert len(after) == len(before)
