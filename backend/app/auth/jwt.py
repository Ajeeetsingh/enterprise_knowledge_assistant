"""JWT creation and verification service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError as PyJWTInvalidTokenError
from jwt.exceptions import PyJWTError

from app.auth.exceptions import TokenExpiredError, TokenInvalidError, TokenTypeError
from app.config import Settings, get_settings

ALLOWED_ALGORITHMS: frozenset[str] = frozenset({"HS256", "HS384", "HS512"})
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _resolve_settings(settings: Settings | None = None) -> Settings:
    resolved = settings or get_settings()
    if resolved.jwt_algorithm not in ALLOWED_ALGORITHMS:
        raise TokenInvalidError("Token configuration is invalid.")
    return resolved


def _encode_token(
    payload: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> str:
    resolved = _resolve_settings(settings)
    return jwt.encode(
        payload,
        resolved.jwt_secret,
        algorithm=resolved.jwt_algorithm,
    )


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    roles: list[str],
    *,
    settings: Settings | None = None,
) -> str:
    """Return a signed JWT access token."""
    resolved = _resolve_settings(settings)
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=resolved.jwt_access_token_expire_minutes)
    user_id_str = str(user_id)

    payload = {
        "sub": user_id_str,
        "user_id": user_id_str,
        "email": email,
        "roles": roles,
        "token_type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": expires_at,
    }
    return _encode_token(payload, settings=resolved)


def create_refresh_token(
    user_id: uuid.UUID,
    *,
    settings: Settings | None = None,
) -> str:
    """Return a signed JWT refresh token."""
    resolved = _resolve_settings(settings)
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=resolved.jwt_refresh_token_expire_days)
    user_id_str = str(user_id)

    payload = {
        "sub": user_id_str,
        "user_id": user_id_str,
        "token_type": REFRESH_TOKEN_TYPE,
        "iat": now,
        "exp": expires_at,
    }
    return _encode_token(payload, settings=resolved)


def decode_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Validate signature and expiration, then return the token payload."""
    resolved = _resolve_settings(settings)
    try:
        return jwt.decode(
            token,
            resolved.jwt_secret,
            algorithms=[resolved.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "token_type"]},
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired.") from exc
    except PyJWTInvalidTokenError as exc:
        raise TokenInvalidError("Token is invalid.") from exc
    except PyJWTError as exc:
        raise TokenInvalidError("Token is invalid.") from exc


def verify_token(
    token: str,
    *,
    expected_type: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Return the decoded payload when the token is valid."""
    payload = decode_token(token, settings=settings)

    token_type = payload.get("token_type")
    if token_type not in {ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE}:
        raise TokenTypeError("Token type is invalid.")

    if expected_type is not None and token_type != expected_type:
        raise TokenTypeError("Token type is invalid.")

    if token_type == ACCESS_TOKEN_TYPE:
        _validate_access_payload(payload)
    else:
        _validate_refresh_payload(payload)

    return payload


def _validate_access_payload(payload: dict[str, Any]) -> None:
    required_fields = ("user_id", "email", "roles")
    for field in required_fields:
        if field not in payload:
            raise TokenInvalidError("Token is invalid.")
    if not isinstance(payload["roles"], list):
        raise TokenInvalidError("Token is invalid.")


def _validate_refresh_payload(payload: dict[str, Any]) -> None:
    if "user_id" not in payload:
        raise TokenInvalidError("Token is invalid.")
