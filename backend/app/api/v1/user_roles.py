"""User role assignment API endpoints (Admin only)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.auth.dependencies import require_permission
from app.auth.permissions import Permission
from app.db.models import User
from app.dependencies import get_db
from app.schemas.roles import AssignRolesRequest, UserRolesResponse
from app.services import role_service, user_service

router = APIRouter()


def _admin_id(user: User) -> str:
    return str(user.id)


def _admin_username(user: User) -> str:
    return user.username or user.email


@router.get("/{user_id}/roles", response_model=UserRolesResponse)
def get_user_roles_endpoint(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.USER_UPDATE)),
) -> UserRolesResponse:
    """Return roles assigned to a user."""
    try:
        roles = role_service.get_user_roles(db, user_id)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return UserRolesResponse.from_user_id_and_roles(user_id, roles)


@router.post("/{user_id}/roles", response_model=UserRolesResponse)
def assign_roles_endpoint(
    user_id: uuid.UUID,
    body: AssignRolesRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_permission(Permission.USER_UPDATE)),
) -> UserRolesResponse:
    """Assign one or more existing roles to a user."""
    try:
        roles = role_service.assign_roles_to_user(db, user_id, body.roles)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except role_service.RoleServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    AuditService.record(
        AuditService.role_assigned(
            admin_id=_admin_id(current_admin),
            admin_username=_admin_username(current_admin),
            target_user_id=str(user_id),
            role_names=body.roles,
        )
    )
    return UserRolesResponse.from_user_id_and_roles(user_id, roles)


@router.delete("/{user_id}/roles/{role_name}", response_model=UserRolesResponse)
def remove_role_endpoint(
    user_id: uuid.UUID,
    role_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_permission(Permission.USER_UPDATE)),
) -> UserRolesResponse:
    """Remove a role from a user."""
    try:
        roles = role_service.remove_role_from_user(db, user_id, role_name)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    AuditService.record(
        AuditService.role_removed(
            admin_id=_admin_id(current_admin),
            admin_username=_admin_username(current_admin),
            target_user_id=str(user_id),
            role_name=role_name,
        )
    )
    return UserRolesResponse.from_user_id_and_roles(user_id, roles)
