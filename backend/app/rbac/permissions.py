"""Role-based permission helpers for API authorization."""

from __future__ import annotations

from app.db.models import User


def get_user_role_names(user: User) -> set[str]:
    """Return the set of role names assigned to a user."""
    return {role.name for role in user.roles}


def user_has_role(user: User, role_name: str) -> bool:
    """Return True when the user has the given role."""
    return role_name in get_user_role_names(user)


def user_has_any_role(user: User, role_names: list[str]) -> bool:
    """Return True when the user has at least one of the given roles."""
    if not role_names:
        return False
    return bool(get_user_role_names(user) & set(role_names))


def user_is_superuser(user: User) -> bool:
    """Return True when the user is marked as a superuser."""
    return user.is_superuser
