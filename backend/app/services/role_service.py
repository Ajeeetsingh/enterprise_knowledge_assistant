"""Role assignment business logic."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.role_permissions import SystemRole, resolve_system_role
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
        resolved = resolve_system_role(role_name)
        lookup_name = resolved.value if resolved is not None else role_name
        if lookup_name in existing_names:
            continue
        role = _get_role_by_name(db, lookup_name)
        if role is None:
            raise RoleNotFoundError(lookup_name)
        user.roles.append(role)
        existing_names.add(lookup_name)

    db.commit()
    return get_user_roles(db, user_id)


def remove_role_from_user(
    db: Session,
    user_id: uuid.UUID,
    role_name: str,
) -> list[Role]:
    """Remove a role from a user; no-op when the role is not assigned."""
    user = user_service.get_user(db, user_id)
    resolved = resolve_system_role(role_name)
    canonical = resolved.value if resolved is not None else role_name
    role = next((item for item in user.roles if item.name == canonical), None)
    if role is None:
        return get_user_roles(db, user_id)

    if role.name == SystemRole.ADMIN.value:
        # Removing Admin may leave the installation without administrators.
        remaining_admin = user.is_superuser or any(
            item.name == SystemRole.ADMIN.value and item is not role
            for item in user.roles
        )
        if not remaining_admin:
            user_service.ensure_not_last_admin(db, user, action="demote")

    user.roles.remove(role)
    db.commit()
    return get_user_roles(db, user_id)


def replace_user_roles(
    db: Session,
    user_id: uuid.UUID,
    role_names: list[str],
) -> list[Role]:
    """Replace a user's roles with *role_names* in one transaction."""
    if not role_names:
        raise RoleServiceError("At least one role is required.", status_code=400)

    user = user_service.get_user(db, user_id)
    resolved_roles: list[Role] = []
    seen: set[str] = set()
    for role_name in role_names:
        resolved = resolve_system_role(role_name)
        if resolved is None:
            raise RoleNotFoundError(role_name)
        if resolved.value in seen:
            continue
        role = _get_role_by_name(db, resolved.value)
        if role is None:
            raise RoleNotFoundError(resolved.value)
        resolved_roles.append(role)
        seen.add(resolved.value)

    losing_admin = (
        user_service.is_administrative_user(user)
        and SystemRole.ADMIN.value not in seen
        and not user.is_superuser
    )
    if losing_admin:
        user_service.ensure_not_last_admin(db, user, action="demote")

    user.roles.clear()
    for role in resolved_roles:
        user.roles.append(role)

    db.commit()
    return get_user_roles(db, user_id)
