"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.audit.service import AuditService
from app.auth.dependencies import require_any_role, require_role, require_superuser
from app.auth.security import get_current_user
from app.db.models import User
from app.dependencies import get_audit_service, get_db
from app.schemas.auth import (
    AuthorizationDemoResponse,
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
)
from app.services import auth_audit_integration, auth_service
from app.services.audit_service import AuditService as PersistedAuditService

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    """Extract the client IP from the request, honouring forwarded headers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("/login", response_model=LoginResponse)
def login_endpoint(
    body: LoginRequest,
    request: Request,
    db=Depends(get_db),
    audit_service: PersistedAuditService = Depends(get_audit_service),
) -> LoginResponse:
    """Authenticate with email and password."""
    ip = _client_ip(request)
    ua = request.headers.get("User-Agent")
    try:
        tokens = auth_service.login(db, body.email, body.password)
    except auth_service.AuthServiceError as exc:
        AuditService.record(
            AuditService.login_failure(
                email=body.email,
                reason=exc.message,
                ip_address=ip,
                user_agent=ua,
            )
        )
        auth_audit_integration.record_login_failed(
            audit_service,
            email=body.email,
            reason=exc.message,
            subject_user_id=exc.subject_user_id,
            ip_address=ip,
            user_agent=ua,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    AuditService.record(
        AuditService.login_success(
            email=body.email,
            ip_address=ip,
            user_agent=ua,
        )
    )
    auth_audit_integration.record_login_success(
        audit_service,
        user_id=tokens.user_id,
        email=body.email,
        ip_address=ip,
        user_agent=ua,
    )
    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh_endpoint(
    body: RefreshRequest,
    db=Depends(get_db),
) -> RefreshResponse:
    """Issue a new access token from a valid refresh token."""
    try:
        access_token = auth_service.refresh_access_token(db, body.refresh_token)
    except auth_service.AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return RefreshResponse(access_token=access_token)


@router.post("/logout", response_model=LogoutResponse)
def logout_endpoint(
    request: Request,
    audit_service: PersistedAuditService = Depends(get_audit_service),
) -> LogoutResponse:
    """Stateless logout — client should discard stored tokens."""
    ip = _client_ip(request)
    ua = request.headers.get("User-Agent")
    AuditService.record(
        AuditService.logout(ip_address=ip)
    )
    auth_audit_integration.record_logout(
        audit_service,
        ip_address=ip,
        user_agent=ua,
    )
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
