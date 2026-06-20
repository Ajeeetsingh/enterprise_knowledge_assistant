"""FastAPI authentication dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated user from a Bearer access token."""
    token = credentials.credentials if credentials is not None else None
    try:
        user = auth_service.get_authenticated_user(db, token)
    except auth_service.AuthServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    request.state.user_id = str(user.id)
    return user
