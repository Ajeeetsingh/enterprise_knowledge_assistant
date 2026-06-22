"""Role-to-permission mapping for system roles.

Maintained in a single location — do not duplicate assignments elsewhere.
Maps Phase 02 system roles to Phase 5.1 permission definitions.
"""

from __future__ import annotations

from enum import StrEnum

from app.auth.permissions import ALL_PERMISSIONS, Permission


class SystemRole(StrEnum):
    """Predefined application roles seeded during Phase 02."""

    ADMIN = "Admin"
    HR = "HR"
    FINANCE = "Finance"
    EMPLOYEE = "Employee"


# Aliases for documentation/spec terminology (e.g. "Administrator").
ROLE_ALIASES: dict[str, SystemRole] = {
    "admin": SystemRole.ADMIN,
    "administrator": SystemRole.ADMIN,
    "hr": SystemRole.HR,
    "finance": SystemRole.FINANCE,
    "employee": SystemRole.EMPLOYEE,
}


ROLE_PERMISSIONS: dict[SystemRole, frozenset[Permission]] = {
    SystemRole.ADMIN: ALL_PERMISSIONS,
    SystemRole.HR: frozenset({
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_UPDATE,
        Permission.KNOWLEDGE_QUERY,
    }),
    SystemRole.FINANCE: frozenset({
        Permission.DOCUMENT_READ,
        Permission.KNOWLEDGE_QUERY,
    }),
    SystemRole.EMPLOYEE: frozenset({
        Permission.DOCUMENT_READ,
        Permission.KNOWLEDGE_QUERY,
    }),
}


def resolve_system_role(role: str | SystemRole | None) -> SystemRole | None:
    """Resolve a role name or alias to a ``SystemRole`` without raising.

    Args:
        role: Canonical role name, alias, or ``SystemRole`` member.

    Returns:
        Matching ``SystemRole``, or ``None`` when *role* is unknown or empty.
    """
    if role is None:
        return None
    if isinstance(role, SystemRole):
        return role
    if not isinstance(role, str):
        return None
    normalized = role.strip()
    if not normalized:
        return None

    for member in SystemRole:
        if normalized == member.value:
            return member

    alias_key = normalized.casefold()
    return ROLE_ALIASES.get(alias_key)


def is_known_role(role: str | SystemRole | None) -> bool:
    """Return whether *role* maps to a predefined system role."""
    return resolve_system_role(role) is not None
