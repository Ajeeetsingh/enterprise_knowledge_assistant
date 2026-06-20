"""Integration tests for authentication API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.jwt import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, create_access_token
from app.config import get_settings
from app.db.models import User
from tests.integration.conftest import TEST_PASSWORD, TEST_SETTINGS

LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"


def test_successful_login(client: TestClient, active_user: User) -> None:
    response = client.post(
        LOGIN_URL,
        json={"email": active_user.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_wrong_password(client: TestClient, active_user: User) -> None:
    response = client.post(
        LOGIN_URL,
        json={"email": active_user.email, "password": "WrongPassword!"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_unknown_email(client: TestClient) -> None:
    response = client.post(
        LOGIN_URL,
        json={"email": "missing@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_disabled_user_login(client: TestClient, inactive_user: User) -> None:
    response = client.post(
        LOGIN_URL,
        json={"email": inactive_user.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is inactive."


def test_successful_refresh(client: TestClient, active_user: User) -> None:
    login_response = client.post(
        LOGIN_URL,
        json={"email": active_user.email, "password": TEST_PASSWORD},
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(REFRESH_URL, json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert data["token_type"] == "bearer"


def test_invalid_refresh_token(client: TestClient) -> None:
    response = client.post(REFRESH_URL, json={"refresh_token": "not-a-valid-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token."


def test_expired_refresh_token(client: TestClient, active_user: User) -> None:
    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(active_user.id),
        "user_id": str(active_user.id),
        "token_type": REFRESH_TOKEN_TYPE,
        "iat": now - timedelta(days=2),
        "exp": now - timedelta(days=1),
    }
    expired_token = jwt.encode(
        expired_payload,
        TEST_SETTINGS.jwt_secret,
        algorithm=TEST_SETTINGS.jwt_algorithm,
    )

    response = client.post(REFRESH_URL, json={"refresh_token": expired_token})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token."


def test_wrong_token_type_on_refresh(client: TestClient, active_user: User) -> None:
    access_token = create_access_token(
        active_user.id,
        active_user.email,
        ["Employee"],
        settings=TEST_SETTINGS,
    )

    response = client.post(REFRESH_URL, json={"refresh_token": access_token})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token."


def test_logout_endpoint(client: TestClient) -> None:
    response = client.post(LOGOUT_URL)

    assert response.status_code == 200
    assert response.json() == {"message": "Logged out successfully."}


def test_login_validation_error(client: TestClient) -> None:
    response = client.post(LOGIN_URL, json={"email": "not-an-email", "password": ""})

    assert response.status_code == 422
