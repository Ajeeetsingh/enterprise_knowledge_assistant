"""Authentication business logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.exceptions import TokenExpiredError, TokenInvalidError, TokenTypeError
from app.auth.jwt import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.auth.password import verify_password
from app.db.models import User


class AuthServiceError(Exception):
    """Base authentication service error with an HTTP status code."""

    def __init__(
        self,
        message: str,
        status_code: int,
        *,
        subject_user_id: uuid.UUID | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.subject_user_id = subject_user_id
        super().__init__(message)


class InvalidCredentialsError(AuthServiceError):
    def __init__(self, *, subject_user_id: uuid.UUID | None = None) -> None:
        super().__init__(
            "Invalid email or password.",
            status_code=401,
            subject_user_id=subject_user_id,
        )


class InactiveAccountError(AuthServiceError):
    def __init__(self, *, subject_user_id: uuid.UUID | None = None) -> None:
        super().__init__(
            "Account is inactive.",
            status_code=403,
            subject_user_id=subject_user_id,
        )


class InvalidRefreshTokenError(AuthServiceError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired refresh token.", status_code=401)


class MissingTokenError(AuthServiceError):
    def __init__(self) -> None:
        super().__init__("Not authenticated.", status_code=401)


class InvalidAccessTokenError(AuthServiceError):
    def __init__(self, *, token_reason: str = "invalid token") -> None:
        super().__init__("Could not validate credentials.", status_code=401)
        self.token_reason = token_reason


class UserNotFoundError(AuthServiceError):
    def __init__(self) -> None:
        super().__init__("User not found.", status_code=404)


@dataclass(frozen=True)
class LoginTokens:
    access_token: str
    refresh_token: str
    user_id: uuid.UUID


def _get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles))
    )


def _get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles))
    )


def _role_names(user: User) -> list[str]:
    return [role.name for role in user.roles]


def login(db: Session, email: str, password: str) -> LoginTokens:
    """Authenticate a user and return access and refresh tokens."""
    user = _get_user_by_email(db, email)
    if user is None:
        raise InvalidCredentialsError()

    if not user.is_active:
        raise InactiveAccountError(subject_user_id=user.id)

    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError(subject_user_id=user.id)

    roles = _role_names(user)
    return LoginTokens(
        access_token=create_access_token(user.id, user.email, roles),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
    )


def refresh_access_token(db: Session, refresh_token: str) -> str:
    """Validate a refresh token and return a new access token."""
    try:
        payload = verify_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    except (TokenExpiredError, TokenInvalidError, TokenTypeError) as exc:
        raise InvalidRefreshTokenError() from exc

    user_id = uuid.UUID(str(payload["user_id"]))
    user = _get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    return create_access_token(user.id, user.email, _role_names(user))


def logout() -> dict[str, str]:
    """Stateless logout — client discards tokens locally."""
    return {"message": "Logged out successfully."}


def get_authenticated_user(db: Session, access_token: str | None) -> User:
    """Validate an access token and return the corresponding active user."""
    if not access_token:
        raise MissingTokenError()

    try:
        payload = verify_token(access_token, expected_type=ACCESS_TOKEN_TYPE)
    except TokenExpiredError as exc:
        raise InvalidAccessTokenError(token_reason="expired token") from exc
    except TokenInvalidError as exc:
        raise InvalidAccessTokenError(token_reason="invalid signature") from exc
    except TokenTypeError as exc:
        raise InvalidAccessTokenError(token_reason="malformed token") from exc

    user_id = uuid.UUID(str(payload["user_id"]))
    user = _get_user_by_id(db, user_id)
    if user is None:
        raise UserNotFoundError()

    if not user.is_active:
        raise InactiveAccountError()

    return user
