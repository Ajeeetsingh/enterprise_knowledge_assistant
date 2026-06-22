"""Centralized permission definitions for the authorization layer.

All permission identifiers are defined here as ``Permission`` enum members.
Do not scatter permission strings across routes, services, or tests.
"""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    """Canonical permission identifiers used throughout the platform.

    Values follow the ``resource:action`` convention for clarity and future
    ABAC extension (attributes can be layered without renaming permissions).
    """

    # Document management
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"

    # Knowledge / RAG
    KNOWLEDGE_QUERY = "knowledge:query"
    KNOWLEDGE_MANAGE = "knowledge:manage"

    # User administration
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Audit (future phases)
    AUDIT_VIEW = "audit:view"


# Logical groupings for documentation, UI, and future policy engines.
DOCUMENT_PERMISSIONS: frozenset[Permission] = frozenset({
    Permission.DOCUMENT_CREATE,
    Permission.DOCUMENT_READ,
    Permission.DOCUMENT_UPDATE,
    Permission.DOCUMENT_DELETE,
})

KNOWLEDGE_PERMISSIONS: frozenset[Permission] = frozenset({
    Permission.KNOWLEDGE_QUERY,
    Permission.KNOWLEDGE_MANAGE,
})

USER_PERMISSIONS: frozenset[Permission] = frozenset({
    Permission.USER_VIEW,
    Permission.USER_CREATE,
    Permission.USER_UPDATE,
    Permission.USER_DELETE,
})

AUDIT_PERMISSIONS: frozenset[Permission] = frozenset({
    Permission.AUDIT_VIEW,
})

PERMISSION_GROUPS: dict[str, frozenset[Permission]] = {
    "document": DOCUMENT_PERMISSIONS,
    "knowledge": KNOWLEDGE_PERMISSIONS,
    "user": USER_PERMISSIONS,
    "audit": AUDIT_PERMISSIONS,
}

ALL_PERMISSIONS: frozenset[Permission] = frozenset(Permission)


def resolve_permission(
    permission: str | Permission | None,
) -> Permission | None:
    """Resolve a permission string or enum member without raising.

    Args:
        permission: Canonical permission value, enum member, or alias string.

    Returns:
        Matching ``Permission``, or ``None`` when *permission* is unknown,
        empty, or not a string/enum.
    """
    if permission is None:
        return None
    if isinstance(permission, Permission):
        return permission
    if not isinstance(permission, str):
        return None

    normalized = permission.strip()
    if not normalized:
        return None

    for member in Permission:
        if normalized == member.value:
            return member

    alias_key = normalized.casefold().replace("_", ":")
    for member in Permission:
        if alias_key == member.value.casefold():
            return member
        enum_name = member.name.casefold().replace("_", ":")
        if alias_key == enum_name:
            return member

    return None


def is_known_permission(permission: str | Permission | None) -> bool:
    """Return whether *permission* maps to a defined permission."""
    return resolve_permission(permission) is not None
