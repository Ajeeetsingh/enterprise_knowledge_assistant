"""Pydantic models for user management API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.db.models import User


class UserCreateRequest(BaseModel):
    """Admin-only user creation. Requires an initial system role."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    username: str | None = Field(default=None, max_length=100)
    role: str = Field(
        min_length=1,
        max_length=100,
        description="Initial system role to assign (Admin, HR, Finance, or Employee).",
    )


class UserUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    is_active: bool


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str | None
    full_name: str
    roles: list[str]
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            roles=[role.name for role in user.roles],
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UserListResponse(BaseModel):
    users: list[UserResponse]
