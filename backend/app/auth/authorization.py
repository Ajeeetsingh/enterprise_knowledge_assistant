"""FastAPI authorization dependencies (RBAC)."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException

from app.auth.security import get_current_user
from app.db.models import User
from app.rbac.permissions import user_has_any_role, user_has_role, user_is_superuser

INSUFFICIENT_PERMISSIONS = "Insufficient permissions."


def _raise_forbidden() -> None:
    raise HTTPException(status_code=403, detail=INSUFFICIENT_PERMISSIONS)


def require_role(role_name: str) -> Callable[..., User]:
    """Require the authenticated user to have a specific role."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not user_has_role(current_user, role_name):
            _raise_forbidden()
        return current_user

    return dependency


def require_any_role(role_names: list[str]) -> Callable[..., User]:
    """Require the authenticated user to have at least one of the given roles."""

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not user_has_any_role(current_user, role_names):
            _raise_forbidden()
        return current_user

    return dependency


def require_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the authenticated user to be a superuser."""
    if not user_is_superuser(current_user):
        _raise_forbidden()
    return current_user
