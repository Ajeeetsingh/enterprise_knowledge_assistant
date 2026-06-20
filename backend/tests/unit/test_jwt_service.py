"""Unit tests for the JWT token service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.exceptions import TokenExpiredError, TokenInvalidError, TokenTypeError
from app.auth.jwt import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from app.config import Settings

TEST_SETTINGS = Settings(
    jwt_secret="test-secret-key-for-jwt-unit-tests-only",
    jwt_algorithm="HS256",
    jwt_access_token_expire_minutes=30,
    jwt_refresh_token_expire_days=7,
)

USER_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
USER_EMAIL = "user@example.com"
USER_ROLES = ["Employee", "HR"]


def test_access_token_creation() -> None:
    token = create_access_token(
        USER_ID,
        USER_EMAIL,
        USER_ROLES,
        settings=TEST_SETTINGS,
    )

    assert isinstance(token, str)
    assert token.count(".") == 2


def test_refresh_token_creation() -> None:
    token = create_refresh_token(USER_ID, settings=TEST_SETTINGS)

    assert isinstance(token, str)
    assert token.count(".") == 2


def test_access_token_payload_contents() -> None:
    token = create_access_token(
        USER_ID,
        USER_EMAIL,
        USER_ROLES,
        settings=TEST_SETTINGS,
    )
    payload = decode_token(token, settings=TEST_SETTINGS)

    assert payload["user_id"] == str(USER_ID)
    assert payload["sub"] == str(USER_ID)
    assert payload["email"] == USER_EMAIL
    assert payload["roles"] == USER_ROLES
    assert payload["token_type"] == ACCESS_TOKEN_TYPE
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_refresh_token_payload_contents() -> None:
    token = create_refresh_token(USER_ID, settings=TEST_SETTINGS)
    payload = decode_token(token, settings=TEST_SETTINGS)

    assert payload["user_id"] == str(USER_ID)
    assert payload["sub"] == str(USER_ID)
    assert payload["token_type"] == REFRESH_TOKEN_TYPE
    assert "email" not in payload
    assert "roles" not in payload
    assert "iat" in payload
    assert "exp" in payload


def test_token_verification() -> None:
    token = create_access_token(
        USER_ID,
        USER_EMAIL,
        USER_ROLES,
        settings=TEST_SETTINGS,
    )

    payload = verify_token(token, settings=TEST_SETTINGS)

    assert payload["email"] == USER_EMAIL
    assert payload["token_type"] == ACCESS_TOKEN_TYPE


def test_invalid_signature_rejection() -> None:
    token = create_access_token(
        USER_ID,
        USER_EMAIL,
        USER_ROLES,
        settings=TEST_SETTINGS,
    )
    tampered = f"{token[:-1]}x"

    with pytest.raises(TokenInvalidError):
        verify_token(tampered, settings=TEST_SETTINGS)


def test_expired_token_rejection() -> None:
    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(USER_ID),
        "user_id": str(USER_ID),
        "email": USER_EMAIL,
        "roles": USER_ROLES,
        "token_type": ACCESS_TOKEN_TYPE,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired_token = jwt.encode(
        expired_payload,
        TEST_SETTINGS.jwt_secret,
        algorithm=TEST_SETTINGS.jwt_algorithm,
    )

    with pytest.raises(TokenExpiredError):
        verify_token(expired_token, settings=TEST_SETTINGS)


def test_wrong_token_type_rejection() -> None:
    refresh_token = create_refresh_token(USER_ID, settings=TEST_SETTINGS)

    with pytest.raises(TokenTypeError):
        verify_token(
            refresh_token,
            expected_type=ACCESS_TOKEN_TYPE,
            settings=TEST_SETTINGS,
        )


def test_malformed_token_rejection() -> None:
    with pytest.raises(TokenInvalidError):
        verify_token("not-a-valid-jwt", settings=TEST_SETTINGS)


def test_rejects_unsupported_configured_algorithm() -> None:
    bad_settings = TEST_SETTINGS.model_copy(update={"jwt_algorithm": "none"})

    with pytest.raises(TokenInvalidError):
        create_access_token(
            USER_ID,
            USER_EMAIL,
            USER_ROLES,
            settings=bad_settings,
        )
