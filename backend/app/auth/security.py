"""FastAPI authentication dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.request_utils import client_ip as _client_ip
from app.db.models import User
from app.db.session import get_db
from app.services.audit_dependencies import get_audit_service
from app.services import security_audit_integration
from app.services.audit_service import AuditService as PersistedAuditService
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    audit_service: PersistedAuditService = Depends(get_audit_service),
) -> User:
    """Return the authenticated user from a Bearer access token."""
    token = credentials.credentials if credentials is not None else None
    ip_address = _client_ip(request)
    user_agent = request.headers.get("User-Agent")
    try:
        user = auth_service.get_authenticated_user(db, token)
    except auth_service.MissingTokenError as exc:
        security_audit_integration.record_unauthorized_access(
            audit_service,
            resource=request.url.path,
            reason="missing token",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except auth_service.InvalidAccessTokenError as exc:
        security_audit_integration.record_invalid_token(
            audit_service,
            reason=exc.token_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except auth_service.InactiveAccountError as exc:
        security_audit_integration.record_unauthorized_access(
            audit_service,
            resource=request.url.path,
            reason=exc.message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except auth_service.AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    request.state.user_id = str(user.id)
    return user
