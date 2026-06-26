"""FastAPI dependencies for persisted audit logging."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository
from app.db.session import get_db
from app.schemas.audit import (
    DEFAULT_AUDIT_LIST_LIMIT,
    MAX_AUDIT_LIST_LIMIT,
    AuditSearchRequest,
)
from app.services.audit_service import AuditService, build_audit_service


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Return a persisted audit service bound to the current database session."""
    return build_audit_service(db)


def get_audit_repository(db: Session = Depends(get_db)) -> AuditRepository:
    """Return an audit repository bound to the current database session."""
    return AuditRepository(db)


def parse_audit_search_request(
    event_type: str | None = Query(default=None, max_length=255),
    event_category: AuditEventCategory | None = Query(default=None),
    status: AuditStatus | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=DEFAULT_AUDIT_LIST_LIMIT, ge=1, le=MAX_AUDIT_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> AuditSearchRequest:
    """Parse and validate audit search query parameters."""
    try:
        return AuditSearchRequest(
            event_type=event_type,
            event_category=event_category,
            status=status,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid search parameters.",
        ) from exc
