"""Pydantic models for authentication API requests and responses."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models import User


class RegisterRequest(BaseModel):
    """Public self-registration payload.

    Privileged fields (role, permissions, is_superuser, is_active) are
    intentionally omitted and rejected via ``extra='forbid'``.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    username: str | None = Field(default=None, max_length=100)


class RegisterResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    message: str = "Account created successfully. You can now sign in."


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str


class AuthorizationDemoResponse(BaseModel):
    message: str


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    roles: list[str]
    is_active: bool
    is_superuser: bool

    @classmethod
    def from_user(cls, user: User) -> CurrentUserResponse:
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            roles=[role.name for role in user.roles],
            is_active=user.is_active,
            is_superuser=user.is_superuser,
        )
