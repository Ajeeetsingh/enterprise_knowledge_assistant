"""Integration tests for GET /api/v1/auth/me."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.auth.jwt import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
)
from app.db.models import User
from tests.integration.conftest import TEST_PASSWORD, TEST_SETTINGS

ME_URL = "/api/v1/auth/me"
LOGIN_URL = "/api/v1/auth/login"


def _bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_successful_me_request(client: TestClient, active_user: User) -> None:
    login_response = client.post(
        LOGIN_URL,
        json={"email": active_user.email, "password": TEST_PASSWORD},
    )
    access_token = login_response.json()["access_token"]

    response = client.get(ME_URL, headers=_bearer_headers(access_token))

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(active_user.id)
    assert data["email"] == active_user.email
    assert data["full_name"] == active_user.full_name
    assert data["roles"] == ["Employee"]
    assert data["is_active"] is True
    assert data["is_superuser"] is False
    assert "password_hash" not in data


def test_missing_authorization_header(client: TestClient) -> None:
    response = client.get(ME_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_invalid_token(client: TestClient) -> None:
    response = client.get(ME_URL, headers=_bearer_headers("not-a-valid-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials."


def test_expired_token(client: TestClient, active_user: User) -> None:
    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(active_user.id),
        "user_id": str(active_user.id),
        "email": active_user.email,
        "roles": ["Employee"],
        "token_type": ACCESS_TOKEN_TYPE,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired_token = jwt.encode(
        expired_payload,
        TEST_SETTINGS.jwt_secret,
        algorithm=TEST_SETTINGS.jwt_algorithm,
    )

    response = client.get(ME_URL, headers=_bearer_headers(expired_token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials."


def test_wrong_token_type(client: TestClient, active_user: User) -> None:
    refresh_token = create_refresh_token(active_user.id, settings=TEST_SETTINGS)

    response = client.get(ME_URL, headers=_bearer_headers(refresh_token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials."


def test_user_not_found(client: TestClient) -> None:
    missing_user_id = uuid.UUID("99999999-9999-4999-8999-999999999999")
    token = create_access_token(
        missing_user_id,
        "ghost@example.com",
        ["Employee"],
        settings=TEST_SETTINGS,
    )

    response = client.get(ME_URL, headers=_bearer_headers(token))

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


def test_inactive_user(client: TestClient, inactive_user: User) -> None:
    token = create_access_token(
        inactive_user.id,
        inactive_user.email,
        ["Employee"],
        settings=TEST_SETTINGS,
    )

    response = client.get(ME_URL, headers=_bearer_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is inactive."
