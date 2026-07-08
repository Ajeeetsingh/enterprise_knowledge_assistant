"""Category-level role-based access control for the RAG engine."""

from __future__ import annotations

from dataclasses import dataclass

VALID_ROLES = frozenset({"admin", "hr", "finance", "employee"})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({"hr", "finance", "security", "employee", "general"}),
    "hr": frozenset({"hr", "employee", "general"}),
    "finance": frozenset({"finance", "general"}),
    "employee": frozenset({"hr", "general"}),
}


@dataclass
class AccessResult:
    """Result of an RBAC check."""

    allowed: bool
    role: str
    category: str
    message: str


class RBACError(PermissionError):
    """Raised when a user lacks permission for a resource."""


def validate_role(role: str) -> str:
    """Validate and normalize a role name."""
    normalized = role.strip().lower()
    if normalized not in VALID_ROLES:
        raise ValueError(
            f"Invalid role '{role}'. Valid roles: {', '.join(sorted(VALID_ROLES))}"
        )
    return normalized


def can_access(role: str, category: str) -> bool:
    """Check whether a role may access documents in a category."""
    normalized_role = validate_role(role)
    allowed_categories = ROLE_PERMISSIONS[normalized_role]
    return category in allowed_categories


def check_access(role: str, category: str) -> AccessResult:
    """Evaluate access and return a structured result."""
    normalized_role = validate_role(role)

    if can_access(normalized_role, category):
        return AccessResult(
            allowed=True,
            role=normalized_role,
            category=category,
            message=f"Access granted for role '{normalized_role}' to '{category}' documents.",
        )

    return AccessResult(
        allowed=False,
        role=normalized_role,
        category=category,
        message=(
            f"Access denied: role '{normalized_role}' cannot access "
            f"'{category}' documents."
        ),
    )


def enforce_access(role: str, category: str) -> None:
    """Raise RBACError if access is not permitted."""
    result = check_access(role, category)
    if not result.allowed:
        raise RBACError(result.message)


def get_accessible_categories(role: str) -> list[str]:
    """Return all document categories accessible to a role."""
    normalized_role = validate_role(role)
    return sorted(ROLE_PERMISSIONS[normalized_role])
