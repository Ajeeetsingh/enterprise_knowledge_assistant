"""Administrator audit search and retrieval API (Phase 7.6)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_audit_admin
from app.db.models import User
from app.db.repositories.audit_repository import AuditRepository, AuditSearchFilter
from app.schemas.audit import AuditLogResponse, AuditSearchRequest, AuditSearchResponse
from app.schemas.errors import ErrorResponse
from app.services.audit_dependencies import get_audit_repository, parse_audit_search_request

router = APIRouter()

_AUDIT_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Only administrators may access audit history.",
    },
    404: {
        "model": ErrorResponse,
        "description": "Audit record not found.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Invalid search parameters.",
    },
}


@router.get(
    "",
    response_model=AuditSearchResponse,
    summary="Search audit logs",
    description=(
        "Return a paginated, filterable list of persisted audit records. "
        "Only administrators and superusers may access audit history."
    ),
    responses=_AUDIT_ERROR_RESPONSES,
)
def list_audit_logs(
    params: AuditSearchRequest = Depends(parse_audit_search_request),
    _: User = Depends(require_audit_admin),
    repository: AuditRepository = Depends(get_audit_repository),
) -> AuditSearchResponse:
    """Search persisted audit logs with optional filters."""
    filters = AuditSearchFilter(
        event_type=params.event_type,
        event_category=params.event_category,
        status=params.status,
        user_id=params.user_id,
        date_from=params.date_from,
        date_to=params.date_to,
    )
    audit_logs, total = repository.search(
        filters=filters,
        limit=params.limit,
        offset=params.offset,
    )
    return AuditSearchResponse(
        items=[AuditLogResponse.from_audit_log(log) for log in audit_logs],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get(
    "/{audit_id}",
    response_model=AuditLogResponse,
    summary="Get audit log by ID",
    description=(
        "Return a single persisted audit record by primary key. "
        "Only administrators and superusers may access audit history."
    ),
    responses=_AUDIT_ERROR_RESPONSES,
)
def get_audit_log(
    audit_id: uuid.UUID,
    _: User = Depends(require_audit_admin),
    repository: AuditRepository = Depends(get_audit_repository),
) -> AuditLogResponse:
    """Return one audit log record."""
    audit_log = repository.get_by_id(audit_id)
    if audit_log is None:
        raise HTTPException(status_code=404, detail="Audit record not found.")
    return AuditLogResponse.from_audit_log(audit_log)
