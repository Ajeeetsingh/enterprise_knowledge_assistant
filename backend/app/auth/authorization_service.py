"""Stateless authorization service for role-based permission checks.

This module is independent of FastAPI, JWT, database models, and business
services. Route protection and dependency injection are added in later
Phase 05 sub-phases.
"""

from __future__ import annotations

from app.auth.permissions import Permission, resolve_permission
from app.auth.role_permissions import ROLE_PERMISSIONS, SystemRole, resolve_system_role


class AuthorizationService:
    """Evaluate permissions granted to predefined system roles.

    All methods are stateless and safe to call from any layer. Unknown roles
    and permissions yield empty results rather than raising exceptions.
    """

    @staticmethod
    def get_permissions(role: str | SystemRole | None) -> frozenset[Permission]:
        """Return all permissions assigned to *role*.

        Args:
            role: Canonical role name, alias (e.g. ``administrator``), or
                ``None``.

        Returns:
            Frozen set of permissions for the resolved role, or an empty set
            when the role is unknown, empty, or invalid.
        """
        resolved = resolve_system_role(role)
        if resolved is None:
            return frozenset()
        return ROLE_PERMISSIONS.get(resolved, frozenset())

    @staticmethod
    def has_permission(
        role: str | SystemRole | None,
        permission: str | Permission | None,
    ) -> bool:
        """Return whether *role* is granted *permission*.

        Args:
            role: Role name or alias to evaluate.
            permission: Permission value or enum member to check.

        Returns:
            ``True`` when the role holds the permission; ``False`` for unknown
            roles, unknown permissions, or empty inputs.
        """
        resolved_role = resolve_system_role(role)
        resolved_permission = resolve_permission(permission)
        if resolved_role is None or resolved_permission is None:
            return False
        return resolved_permission in ROLE_PERMISSIONS.get(resolved_role, frozenset())

    @staticmethod
    def has_any_permission(
        role: str | SystemRole | None,
        permissions: list[str | Permission] | None,
    ) -> bool:
        """Return whether *role* holds at least one of *permissions*.

        Args:
            role: Role name or alias to evaluate.
            permissions: Permission values to check. Empty or ``None`` lists
                always return ``False``.

        Returns:
            ``True`` when any listed permission is granted to the role.
        """
        if not permissions:
            return False
        granted = AuthorizationService.get_permissions(role)
        for item in permissions:
            resolved = resolve_permission(item)
            if resolved is not None and resolved in granted:
                return True
        return False

    @staticmethod
    def has_all_permissions(
        role: str | SystemRole | None,
        permissions: list[str | Permission] | None,
    ) -> bool:
        """Return whether *role* holds every permission in *permissions*.

        Args:
            role: Role name or alias to evaluate.
            permissions: Permission values that must all be present. Empty or
                ``None`` lists return ``True`` (vacuously satisfied).

        Returns:
            ``True`` when all listed permissions are granted to the role.
        """
        if not permissions:
            return True
        granted = AuthorizationService.get_permissions(role)
        for item in permissions:
            resolved = resolve_permission(item)
            if resolved is None or resolved not in granted:
                return False
        return True
