"""Authorization policy — category rules delegated to RAG engine for MVP."""

from app.rag.rbac import (
    AccessResult,
    RBACError,
    can_access,
    check_access,
    enforce_access,
    get_accessible_categories,
    validate_role,
)

__all__ = [
    "AccessResult",
    "RBACError",
    "can_access",
    "check_access",
    "enforce_access",
    "get_accessible_categories",
    "validate_role",
]
