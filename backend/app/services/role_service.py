"""Role assignment business logic."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Role
from app.services import user_service


class RoleServiceError(Exception):
    """Base role service error with an HTTP status code."""

    def __init__(self, message: str, status_code: int) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class RoleNotFoundError(RoleServiceError):
    def __init__(self, role_name: str) -> None:
        super().__init__(f"Role '{role_name}' not found.", status_code=404)


def list_roles(db: Session) -> list[Role]:
    """Return all available roles ordered by name."""
    return list(db.scalars(select(Role).order_by(Role.name)))


def _get_role_by_name(db: Session, role_name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == role_name))


def get_user_roles(db: Session, user_id: uuid.UUID) -> list[Role]:
    """Return roles assigned to a user."""
    user = user_service.get_user(db, user_id)
    return sorted(user.roles, key=lambda role: role.name)


def assign_roles_to_user(
    db: Session,
    user_id: uuid.UUID,
    role_names: list[str],
) -> list[Role]:
    """Assign one or more existing roles; skip roles already assigned."""
    user = user_service.get_user(db, user_id)
    existing_names = {role.name for role in user.roles}

    for role_name in role_names:
        if role_name in existing_names:
            continue
        role = _get_role_by_name(db, role_name)
        if role is None:
            raise RoleNotFoundError(role_name)
        user.roles.append(role)
        existing_names.add(role_name)

    db.commit()
    return get_user_roles(db, user_id)


def remove_role_from_user(
    db: Session,
    user_id: uuid.UUID,
    role_name: str,
) -> list[Role]:
    """Remove a role from a user; no-op when the role is not assigned."""
    user = user_service.get_user(db, user_id)
    role = next((item for item in user.roles if item.name == role_name), None)
    if role is not None:
        user.roles.remove(role)
        db.commit()
    return get_user_roles(db, user_id)
