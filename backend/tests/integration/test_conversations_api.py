"""Integration tests for conversation management API (Phase 6.5)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import User
from app.services.conversation_service import build_conversation_service
from tests.constants import TEST_PASSWORD_HASH
from tests.integration.conftest import access_token_for, bearer_headers

BASE_URL = "/api/v1/conversations"

PUBLIC_CONVERSATION_FIELDS = {"id", "title", "created_at", "updated_at"}
PUBLIC_MESSAGE_FIELDS = {
    "id",
    "role",
    "content",
    "citations",
    "confidence_score",
    "created_at",
}
INTERNAL_FIELDS = {"user_id", "conversation_id", "_citations"}


@pytest.fixture
def other_user(db_session: Session, employee_role) -> User:
    user = User(
        email="other@example.com",
        username="other",
        full_name="Other User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(employee_role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_conversation(
    client: TestClient,
    token: str,
    *,
    title: str | None = "HR Questions",
) -> dict:
    body = {} if title is None else {"title": title}
    response = client.post(BASE_URL, headers=bearer_headers(token), json=body)
    assert response.status_code == 201
    return response.json()


class TestConversationAuthentication:
    def test_create_requires_authentication(self, client: TestClient) -> None:
        response = client.post(BASE_URL, json={"title": "HR Questions"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated."

    def test_list_requires_authentication(self, client: TestClient) -> None:
        response = client.get(BASE_URL)
        assert response.status_code == 401

    def test_get_requires_authentication(self, client: TestClient) -> None:
        response = client.get(f"{BASE_URL}/{uuid.uuid4()}")
        assert response.status_code == 401

    def test_delete_requires_authentication(self, client: TestClient) -> None:
        response = client.delete(f"{BASE_URL}/{uuid.uuid4()}")
        assert response.status_code == 401

    def test_rename_requires_authentication(self, client: TestClient) -> None:
        response = client.put(
            f"{BASE_URL}/{uuid.uuid4()}",
            json={"title": "New Title"},
        )
        assert response.status_code == 401

    def test_messages_requires_authentication(self, client: TestClient) -> None:
        response = client.get(f"{BASE_URL}/{uuid.uuid4()}/messages")
        assert response.status_code == 401


class TestCreateConversation:
    def test_create_with_title(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        data = _create_conversation(client, token, title="HR Questions")

        assert set(data.keys()) == PUBLIC_CONVERSATION_FIELDS
        assert data["title"] == "HR Questions"
        assert uuid.UUID(data["id"])

    def test_create_without_title(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.post(BASE_URL, headers=bearer_headers(token), json={})
        assert response.status_code == 201
        assert response.json()["title"] is None

    def test_create_trims_title(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.post(
            BASE_URL,
            headers=bearer_headers(token),
            json={"title": "  HR Questions  "},
        )
        assert response.status_code == 201
        assert response.json()["title"] == "HR Questions"


class TestListConversations:
    def test_list_empty(self, client: TestClient, active_user: User) -> None:
        token = access_token_for(active_user)
        response = client.get(BASE_URL, headers=bearer_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_returns_owned_conversations_only(
        self,
        client: TestClient,
        active_user: User,
        other_user: User,
    ) -> None:
        owner_token = access_token_for(active_user)
        other_token = access_token_for(other_user)

        _create_conversation(client, owner_token, title="Owner conversation")
        _create_conversation(client, other_token, title="Other conversation")

        response = client.get(BASE_URL, headers=bearer_headers(owner_token))
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Owner conversation"

    def test_list_pagination(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        for index in range(3):
            _create_conversation(client, token, title=f"Conversation {index}")

        page_one = client.get(
            f"{BASE_URL}?limit=2&offset=0",
            headers=bearer_headers(token),
        )
        page_two = client.get(
            f"{BASE_URL}?limit=2&offset=2",
            headers=bearer_headers(token),
        )

        assert page_one.status_code == 200
        assert page_two.status_code == 200
        assert page_one.json()["total"] == 3
        assert len(page_one.json()["items"]) == 2
        assert len(page_two.json()["items"]) == 1

    def test_list_invalid_limit_returns_422(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.get(
            f"{BASE_URL}?limit=0",
            headers=bearer_headers(token),
        )
        assert response.status_code == 422


class TestGetConversation:
    def test_get_owned_conversation(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        created = _create_conversation(client, token)

        response = client.get(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert set(data.keys()) == PUBLIC_CONVERSATION_FIELDS

    def test_get_not_found(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.get(
            f"{BASE_URL}/{uuid.uuid4()}",
            headers=bearer_headers(token),
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found."

    def test_get_foreign_conversation_returns_403(
        self,
        client: TestClient,
        active_user: User,
        other_user: User,
    ) -> None:
        owner_token = access_token_for(active_user)
        other_token = access_token_for(other_user)
        created = _create_conversation(client, owner_token)

        response = client.get(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(other_token),
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "You do not have access to this conversation."


class TestRenameConversation:
    def test_rename_owned_conversation(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        created = _create_conversation(client, token, title="Old Title")

        response = client.put(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
            json={"title": "New Title"},
        )
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == PUBLIC_CONVERSATION_FIELDS
        assert data["id"] == created["id"]
        assert data["title"] == "New Title"

        get_response = client.get(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
        )
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "New Title"

    def test_rename_trims_title(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        created = _create_conversation(client, token)

        response = client.put(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
            json={"title": "  Trimmed Title  "},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Trimmed Title"

    def test_rename_not_found(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.put(
            f"{BASE_URL}/{uuid.uuid4()}",
            headers=bearer_headers(token),
            json={"title": "New Title"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Conversation not found."

    def test_rename_foreign_conversation_returns_403(
        self,
        client: TestClient,
        active_user: User,
        other_user: User,
    ) -> None:
        owner_token = access_token_for(active_user)
        other_token = access_token_for(other_user)
        created = _create_conversation(client, owner_token)

        response = client.put(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(other_token),
            json={"title": "Stolen Title"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "You do not have access to this conversation."

    def test_rename_blank_title_returns_422(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        created = _create_conversation(client, token)

        response = client.put(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
            json={"title": "   "},
        )
        assert response.status_code == 422

    def test_rename_missing_title_returns_422(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        created = _create_conversation(client, token)

        response = client.put(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
            json={},
        )
        assert response.status_code == 422

    def test_rename_title_too_long_returns_422(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        created = _create_conversation(client, token)

        response = client.put(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
            json={"title": "x" * 501},
        )
        assert response.status_code == 422


class TestDeleteConversation:
    def test_delete_owned_conversation(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        created = _create_conversation(client, token)

        response = client.delete(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert "deleted" in data["message"].lower()

        get_response = client.get(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(token),
        )
        assert get_response.status_code == 404

    def test_delete_foreign_conversation_returns_403(
        self,
        client: TestClient,
        active_user: User,
        other_user: User,
    ) -> None:
        owner_token = access_token_for(active_user)
        other_token = access_token_for(other_user)
        created = _create_conversation(client, owner_token)

        response = client.delete(
            f"{BASE_URL}/{created['id']}",
            headers=bearer_headers(other_token),
        )
        assert response.status_code == 403


class TestConversationMessages:
    def test_empty_history(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        created = _create_conversation(client, token)

        response = client.get(
            f"{BASE_URL}/{created['id']}/messages",
            headers=bearer_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_history_ordered_oldest_to_newest(
        self,
        client: TestClient,
        db_session: Session,
        active_user: User,
    ) -> None:
        token = access_token_for(active_user)
        service = build_conversation_service(db_session)
        conversation = service.create_conversation(active_user, title="History")
        service.add_user_message(
            active_user,
            conversation.id,
            "What is our maternity leave policy?",
        )
        service.add_assistant_message(
            active_user,
            conversation.id,
            "16 weeks of paid leave.",
            citations=[{"source": "handbook.pdf", "page": 12}],
            confidence_score=0.91,
        )

        response = client.get(
            f"{BASE_URL}/{conversation.id}/messages",
            headers=bearer_headers(token),
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 2
        assert items[0]["role"] == "user"
        assert items[1]["role"] == "assistant"
        assert items[0]["content"] == "What is our maternity leave policy?"
        assert items[1]["citations"] == [{"source": "handbook.pdf", "page": 12}]
        assert items[1]["confidence_score"] == 0.91
        for item in items:
            assert set(item.keys()) == PUBLIC_MESSAGE_FIELDS
            assert not INTERNAL_FIELDS.intersection(item.keys())

    def test_messages_foreign_conversation_returns_403(
        self,
        client: TestClient,
        active_user: User,
        other_user: User,
    ) -> None:
        owner_token = access_token_for(active_user)
        other_token = access_token_for(other_user)
        created = _create_conversation(client, owner_token)

        response = client.get(
            f"{BASE_URL}/{created['id']}/messages",
            headers=bearer_headers(other_token),
        )
        assert response.status_code == 403


class TestConversationValidation:
    def test_title_too_long_returns_422(
        self, client: TestClient, active_user: User
    ) -> None:
        token = access_token_for(active_user)
        response = client.post(
            BASE_URL,
            headers=bearer_headers(token),
            json={"title": "x" * 501},
        )
        assert response.status_code == 422
