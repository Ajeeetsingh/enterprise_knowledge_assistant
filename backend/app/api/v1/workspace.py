"""Authenticated workspace summary API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.db.models import User
from app.dependencies import get_db, get_document_service_dep
from app.schemas.errors import ErrorResponse
from app.schemas.workspace import WorkspaceSummaryResponse
from app.services.document_service import DocumentService
from app.services.workspace_service import build_workspace_service

router = APIRouter()

_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
}


@router.get(
    "/summary",
    response_model=WorkspaceSummaryResponse,
    summary="Get personal workspace summary",
    description=(
        "Return document, conversation, and question counts for the "
        "authenticated user. Used by the home dashboard."
    ),
    responses=_ERROR_RESPONSES,
)
def get_workspace_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    document_service: DocumentService = Depends(get_document_service_dep),
) -> WorkspaceSummaryResponse:
    """Return per-user workspace KPIs."""
    service = build_workspace_service(db, document_service)
    return service.get_summary(current_user)
