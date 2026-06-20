"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.authorization import require_any_role, require_role, require_superuser
from app.auth.security import get_current_user
from app.db.models import User
from app.dependencies import get_db
from app.schemas.auth import (
    AuthorizationDemoResponse,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login_endpoint(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate with email and password."""
    try:
        tokens = auth_service.login(db, body.email, body.password)
    except auth_service.AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh_endpoint(
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> RefreshResponse:
    """Issue a new access token from a valid refresh token."""
    try:
        access_token = auth_service.refresh_access_token(db, body.refresh_token)
    except auth_service.AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return RefreshResponse(access_token=access_token)


@router.post("/logout", response_model=LogoutResponse)
def logout_endpoint() -> LogoutResponse:
    """Stateless logout — client should discard stored tokens."""
    result = auth_service.logout()
    return LogoutResponse(message=result["message"])


@router.get("/me", response_model=CurrentUserResponse)
def me_endpoint(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """Return the currently authenticated user profile."""
    return CurrentUserResponse.from_user(current_user)


@router.get("/admin-demo", response_model=AuthorizationDemoResponse)
def admin_demo_endpoint(
    current_user: User = Depends(require_role("Admin")),
) -> AuthorizationDemoResponse:
    """Demonstration endpoint — Admin role required."""
    return AuthorizationDemoResponse(message="Admin access granted.")


@router.get("/hr-demo", response_model=AuthorizationDemoResponse)
def hr_demo_endpoint(
    current_user: User = Depends(require_any_role(["Admin", "HR"])),
) -> AuthorizationDemoResponse:
    """Demonstration endpoint — Admin or HR role required."""
    return AuthorizationDemoResponse(message="HR or Admin access granted.")


@router.get("/superuser-demo", response_model=AuthorizationDemoResponse)
def superuser_demo_endpoint(
    current_user: User = Depends(require_superuser),
) -> AuthorizationDemoResponse:
    """Demonstration endpoint — superuser flag required."""
    return AuthorizationDemoResponse(message="Superuser access granted.")
