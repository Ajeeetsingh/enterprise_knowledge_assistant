"""Integration tests for user management API."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.db.models import User
from app.auth.dependencies import AUTHORIZATION_DENIED_MESSAGE
from tests.integration.conftest import TEST_PASSWORD, access_token_for

USERS_URL = "/api/v1/users"


def _bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_list_users(client: TestClient, admin_user: User, active_user: User) -> None:
    token = access_token_for(admin_user)
    response = client.get(USERS_URL, headers=_bearer_headers(token))

    assert response.status_code == 200
    data = response.json()
    emails = {user["email"] for user in data["users"]}
    assert admin_user.email in emails
    assert active_user.email in emails
    for user in data["users"]:
        assert "password_hash" not in user


def test_create_user(client: TestClient, admin_user: User) -> None:
    token = access_token_for(admin_user)
    response = client.post(
        USERS_URL,
        headers=_bearer_headers(token),
        json={
            "email": "newuser@example.com",
            "password": "NewUserPass1!",
            "full_name": "New User",
            "username": "newuser",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert data["username"] == "newuser"
    assert data["is_active"] is True
    assert data["roles"] == []
    assert "password_hash" not in data


def test_duplicate_email(client: TestClient, admin_user: User, active_user: User) -> None:
    token = access_token_for(admin_user)
    response = client.post(
        USERS_URL,
        headers=_bearer_headers(token),
        json={
            "email": active_user.email,
            "password": "AnotherPass1!",
            "full_name": "Duplicate User",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "A user with this email already exists."


def test_update_user(client: TestClient, admin_user: User, active_user: User) -> None:
    token = access_token_for(admin_user)
    response = client.put(
        f"{USERS_URL}/{active_user.id}",
        headers=_bearer_headers(token),
        json={
            "full_name": "Updated Name",
            "email": "updated@example.com",
            "is_active": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["email"] == "updated@example.com"
    assert data["is_active"] is True


def test_soft_delete_user(client: TestClient, admin_user: User, active_user: User) -> None:
    token = access_token_for(admin_user)
    response = client.delete(
        f"{USERS_URL}/{active_user.id}",
        headers=_bearer_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False

    get_response = client.get(
        f"{USERS_URL}/{active_user.id}",
        headers=_bearer_headers(token),
    )
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False


def test_non_admin_forbidden(client: TestClient, active_user: User) -> None:
    token = access_token_for(active_user)
    response = client.get(USERS_URL, headers=_bearer_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


def test_invalid_user_id(client: TestClient, admin_user: User) -> None:
    token = access_token_for(admin_user)
    missing_id = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    response = client.get(
        f"{USERS_URL}/{missing_id}",
        headers=_bearer_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."
