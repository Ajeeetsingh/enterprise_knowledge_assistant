"""Pydantic models for role management API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import Role


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_role(cls, role: Role) -> RoleResponse:
        return cls(
            id=role.id,
            name=role.name,
            description=role.description,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )


class RoleListResponse(BaseModel):
    roles: list[RoleResponse]


class AssignRolesRequest(BaseModel):
    roles: list[str] = Field(min_length=1)


class UserRolesResponse(BaseModel):
    user_id: uuid.UUID
    roles: list[str]

    @classmethod
    def from_user_id_and_roles(
        cls,
        user_id: uuid.UUID,
        roles: list[Role],
    ) -> UserRolesResponse:
        return cls(
            user_id=user_id,
            roles=[role.name for role in roles],
        )
