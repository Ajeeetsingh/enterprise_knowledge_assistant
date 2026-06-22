"""FastAPI authorization dependencies (Phase 5.3).

Reusable dependency factories integrate JWT authentication with the
stateless ``AuthorizationService``. Role normalization and permission
evaluation live exclusively in this module — routes must not implement
their own authorization logic.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable

from fastapi import Depends, HTTPException, Request

from app.audit.service import AuditService
from app.auth.authorization_service import AuthorizationService
from app.auth.permissions import Permission, resolve_permission
from app.auth.role_permissions import SystemRole, resolve_system_role
from app.auth.security import get_current_user
from app.core.logging import get_logger
from app.db.models import User
from app.db.models.document import Document

logger = get_logger(__name__)

AUTHORIZATION_DENIED_MESSAGE = (
    "You do not have permission to perform this action."
)


def normalize_role_names(
    role_names: Iterable[str | SystemRole | None] | None,
) -> frozenset[SystemRole]:
    """Normalize, deduplicate, and filter role names to canonical system roles.

    Unknown aliases, empty strings, unsupported types, and malformed entries
    are ignored without raising exceptions.

    Args:
        role_names: Raw role names from user assignments, document metadata,
            or route requirements.

    Returns:
        Frozen set of canonical ``SystemRole`` members.
    """
    if role_names is None:
        return frozenset()
    normalized: set[SystemRole] = set()
    for item in role_names:
        resolved = resolve_system_role(item)
        if resolved is not None:
            normalized.add(resolved)
    return frozenset(normalized)


def normalize_allowed_roles(
    allowed_roles: list[str] | None,
) -> frozenset[SystemRole]:
    """Normalize document ``allowed_roles`` metadata for authorization checks.

    This function does not read from or modify the Document model. Callers
    pass the list returned by ``Document.allowed_roles``.

    Args:
        allowed_roles: Role name strings from document metadata.

    Returns:
        Canonical, deduplicated system roles. Unknown names are omitted.
    """
    return normalize_role_names(allowed_roles)


def get_user_system_roles(user: User) -> frozenset[SystemRole]:
    """Return the canonical system roles assigned to *user*."""
    return normalize_role_names(role.name for role in user.roles)


def get_user_permissions(user: User) -> frozenset[Permission]:
    """Return the union of permissions granted by all of the user's roles."""
    granted: set[Permission] = set()
    for role in get_user_system_roles(user):
        granted.update(AuthorizationService.get_permissions(role))
    return frozenset(granted)


def user_has_permission(
    user: User,
    permission: str | Permission | None,
) -> bool:
    """Return whether *user* holds *permission* via any assigned role."""
    resolved_permission = resolve_permission(permission)
    if resolved_permission is None:
        return False
    for role in get_user_system_roles(user):
        if AuthorizationService.has_permission(role, resolved_permission):
            return True
    return False


def user_has_any_permission(
    user: User,
    permissions: list[str | Permission] | None,
) -> bool:
    """Return whether *user* holds at least one listed permission."""
    if not permissions:
        return False
    granted = get_user_permissions(user)
    for item in permissions:
        resolved = resolve_permission(item)
        if resolved is not None and resolved in granted:
            return True
    return False


def user_has_all_permissions(
    user: User,
    permissions: list[str | Permission] | None,
) -> bool:
    """Return whether *user* holds every listed permission."""
    if not permissions:
        return True
    granted = get_user_permissions(user)
    for item in permissions:
        resolved = resolve_permission(item)
        if resolved is None or resolved not in granted:
            return False
    return True


def user_has_role(user: User, role: str | SystemRole | None) -> bool:
    """Return whether *user* has the normalized target role."""
    target = resolve_system_role(role)
    if target is None:
        return False
    return target in get_user_system_roles(user)


def user_has_any_role(
    user: User,
    roles: list[str | SystemRole] | None,
) -> bool:
    """Return whether *user* has at least one of the normalized target roles."""
    if not roles:
        return False
    targets = normalize_role_names(roles)
    if not targets:
        return False
    return bool(get_user_system_roles(user) & targets)


def _user_identifier(user: User) -> str:
    return user.username or user.email


def _log_authorization_denied(
    *,
    request: Request,
    user: User,
    check_type: str,
    check_value: str,
) -> None:
    event = AuditService.permission_denied(
        user_id=str(user.id),
        username=_user_identifier(user),
        permission=f"{check_type}:{check_value}",
        endpoint=request.url.path,
    )
    AuditService.record(event)


def _raise_forbidden() -> None:
    raise HTTPException(status_code=403, detail=AUTHORIZATION_DENIED_MESSAGE)


def require_permission(
    permission: str | Permission,
) -> Callable[..., User]:
    """Require the authenticated user to hold a specific permission."""

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not user_has_permission(current_user, permission):
            resolved = resolve_permission(permission)
            check_value = resolved.value if resolved is not None else str(permission)
            _log_authorization_denied(
                request=request,
                user=current_user,
                check_type="permission",
                check_value=check_value,
            )
            _raise_forbidden()
        return current_user

    return dependency


def require_all_permissions(
    permissions: list[str | Permission],
) -> Callable[..., User]:
    """Require the authenticated user to hold every listed permission."""

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not user_has_all_permissions(current_user, permissions):
            resolved_values = [
                resolved.value
                for item in permissions
                if (resolved := resolve_permission(item)) is not None
            ]
            _log_authorization_denied(
                request=request,
                user=current_user,
                check_type="permissions",
                check_value=",".join(resolved_values) or "unknown",
            )
            _raise_forbidden()
        return current_user

    return dependency


def require_role(role: str | SystemRole) -> Callable[..., User]:
    """Require the authenticated user to have a specific system role."""

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not user_has_role(current_user, role):
            resolved = resolve_system_role(role)
            check_value = resolved.value if resolved is not None else str(role)
            _log_authorization_denied(
                request=request,
                user=current_user,
                check_type="role",
                check_value=check_value,
            )
            _raise_forbidden()
        return current_user

    return dependency


def require_any_role(
    role_names: list[str | SystemRole],
) -> Callable[..., User]:
    """Require the authenticated user to have at least one of the given roles."""

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not user_has_any_role(current_user, role_names):
            targets = normalize_role_names(role_names)
            check_value = ",".join(sorted(role.value for role in targets)) or "unknown"
            _log_authorization_denied(
                request=request,
                user=current_user,
                check_type="roles",
                check_value=check_value,
            )
            _raise_forbidden()
        return current_user

    return dependency


def require_superuser(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the authenticated user to be a superuser."""
    if not current_user.is_superuser:
        _log_authorization_denied(
            request=request,
            user=current_user,
            check_type="superuser",
            check_value="true",
        )
        _raise_forbidden()
    return current_user


def require_document_access(
    action: str = "read",
) -> Callable[..., Document]:
    """Return a FastAPI dependency that enforces document-level authorization.

    The dependency resolves the document from the repository, applies the
    ``DocumentAuthorizationService`` visibility / role / owner rules, and
    either returns the loaded ``Document`` (granted) or raises HTTP 403
    (denied).

    Usage in a route::

        @router.get("/{document_id}")
        def get_document(
            document: Document = Depends(require_document_access("read")),
        ) -> ...:

    Args:
        action: Descriptive action string forwarded to the authorization
            service (``"read"``, ``"delete"``, ``"update"``, ``"manage"``).
            Affects only the log message; the authorization rules are
            identical for all document-scoped actions in this phase.

    Returns:
        A FastAPI dependency callable that resolves to the authorized
        ``Document``.
    """
    from app.auth.document_authorization import DocumentAuthorizationService
    from app.db.repositories.document_repository import DocumentRepository
    from app.dependencies import get_document_repository
    from app.core.exceptions import DocumentNotFoundError

    def dependency(
        document_id: uuid.UUID,
        request: Request,
        current_user: User = Depends(get_current_user),
        repository: DocumentRepository = Depends(get_document_repository),
    ) -> Document:
        document = repository.get_by_id(document_id)
        if document is None:
            from fastapi import HTTPException as _HTTPException
            raise _HTTPException(status_code=404, detail="Document not found.")

        if action == "read":
            decision = DocumentAuthorizationService.can_read_document(
                current_user, document
            )
        elif action == "delete":
            decision = DocumentAuthorizationService.can_delete_document(
                current_user, document
            )
        elif action == "update":
            decision = DocumentAuthorizationService.can_update_document(
                current_user, document
            )
        else:
            decision = DocumentAuthorizationService.can_manage_document(
                current_user, document
            )

        if not decision.granted:
            AuditService.record(
                AuditService.document_access_denied(
                    user_id=str(current_user.id),
                    username=_user_identifier(current_user),
                    document_id=str(document_id),
                    action=action,
                    reason=decision.reason,
                    endpoint=request.url.path,
                )
            )
            _raise_forbidden()

        return document

    return dependency
