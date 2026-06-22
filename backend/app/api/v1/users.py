"""User management API endpoints (Admin only)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.auth.dependencies import require_permission
from app.auth.permissions import Permission
from app.db.models import User
from app.dependencies import get_db
from app.schemas.users import (
    UserCreateRequest,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services import user_service

router = APIRouter()


def _admin_id(user: User) -> str:
    return str(user.id)


def _admin_username(user: User) -> str:
    return user.username or user.email


@router.get("", response_model=UserListResponse)
def list_users_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.USER_VIEW)),
) -> UserListResponse:
    """List all users."""
    users = user_service.list_users(db)
    return UserListResponse(users=[UserResponse.from_user(user) for user in users])


@router.get("/{user_id}", response_model=UserResponse)
def get_user_endpoint(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(Permission.USER_VIEW)),
) -> UserResponse:
    """Return a single user by ID."""
    try:
        user = user_service.get_user(db, user_id)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return UserResponse.from_user(user)


@router.post("", response_model=UserResponse, status_code=201)
def create_user_endpoint(
    body: UserCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_permission(Permission.USER_CREATE)),
) -> UserResponse:
    """Create a new user."""
    try:
        user = user_service.create_user(
            db,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            username=body.username,
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    AuditService.record(
        AuditService.user_created(
            admin_id=_admin_id(current_admin),
            admin_username=_admin_username(current_admin),
            target_user_id=str(user.id),
            target_email=user.email,
        )
    )
    return UserResponse.from_user(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user_endpoint(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_permission(Permission.USER_UPDATE)),
) -> UserResponse:
    """Update user profile fields."""
    try:
        user = user_service.update_user(
            db,
            user_id,
            full_name=body.full_name,
            email=body.email,
            is_active=body.is_active,
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    AuditService.record(
        AuditService.user_updated(
            admin_id=_admin_id(current_admin),
            admin_username=_admin_username(current_admin),
            target_user_id=str(user_id),
        )
    )
    return UserResponse.from_user(user)


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user_endpoint(
    user_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_permission(Permission.USER_DELETE)),
) -> UserResponse:
    """Soft-delete a user by setting is_active to false."""
    try:
        user = user_service.soft_delete_user(db, user_id)
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    AuditService.record(
        AuditService.user_deleted(
            admin_id=_admin_id(current_admin),
            admin_username=_admin_username(current_admin),
            target_user_id=str(user_id),
        )
    )
    return UserResponse.from_user(user)
