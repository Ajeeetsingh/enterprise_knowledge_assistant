"""Pydantic models for authentication API requests and responses."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.db.models import User


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
