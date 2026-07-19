"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.audit.service import AuditService
from app.auth.dependencies import require_any_role, require_role, require_superuser
from app.auth.security import get_current_user
from app.config import get_settings
from app.core.rate_limit import enforce_rate_limit
from app.core.request_utils import client_ip as _client_ip
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
    RegisterRequest,
    RegisterResponse,
)
from app.services import auth_audit_integration, auth_service, user_service
from app.services.audit_service import AuditService as PersistedAuditService

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register_endpoint(
    body: RegisterRequest,
    request: Request,
    db=Depends(get_db),
) -> RegisterResponse:
    """Public self-registration. Always assigns the Employee role server-side."""
    enforce_rate_limit(
        request,
        bucket="auth-register",
        max_calls=5,
        window_seconds=3600,
        detail="Too many registration attempts. Please try again later.",
    )
    try:
        user = user_service.register_public_user(
            db,
            email=str(body.email),
            password=body.password,
            full_name=body.full_name,
            username=body.username,
        )
    except user_service.UserServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    return RegisterResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
    )


@router.post("/login", response_model=LoginResponse)
def login_endpoint(
    body: LoginRequest,
    request: Request,
    db=Depends(get_db),
    audit_service: PersistedAuditService = Depends(get_audit_service),
) -> LoginResponse:
    """Authenticate with email and password."""
    enforce_rate_limit(
        request,
        bucket="auth-login",
        max_calls=10,
        window_seconds=60,
        detail="Too many login attempts. Please try again later.",
    )
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
    request: Request,
    db=Depends(get_db),
) -> RefreshResponse:
    """Issue a new access token from a valid refresh token."""
    enforce_rate_limit(
        request,
        bucket="auth-refresh",
        max_calls=30,
        window_seconds=60,
        detail="Too many token refresh attempts. Please try again later.",
    )
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


def _register_authorization_demo_routes() -> None:
    """Expose role demo endpoints only outside production."""
    if get_settings().app_env != "development":
        return

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


_register_authorization_demo_routes()