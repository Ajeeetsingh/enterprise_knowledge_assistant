"""Knowledge Domains API endpoints (Phase 1)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import require_permission
from app.auth.permissions import Permission
from app.core.logging import get_logger, log_with_fields
from app.db.models import User
from app.dependencies import get_knowledge_domain_service
from app.schemas.knowledge_domains import (
    KnowledgeDomainCreateRequest,
    KnowledgeDomainListResponse,
    KnowledgeDomainResponse,
)
from app.schemas.errors import ErrorResponse
from app.services.knowledge_domain_service import KnowledgeDomainService

router = APIRouter()
logger = get_logger(__name__)

_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Authenticated user lacks required permission.",
    },
    409: {
        "model": ErrorResponse,
        "description": "A knowledge domain with this name already exists.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Request validation failed.",
    },
}


@router.get(
    "",
    response_model=KnowledgeDomainListResponse,
    summary="List knowledge domains",
    description="Return all knowledge domains sorted alphabetically by name.",
    responses=_ERROR_RESPONSES,
)
def list_knowledge_domains(
    service: KnowledgeDomainService = Depends(get_knowledge_domain_service),
    _: User = Depends(require_permission(Permission.KNOWLEDGE_QUERY)),
) -> KnowledgeDomainListResponse:
    """List knowledge domains (alphabetically)."""
    domains = service.list_domains()
    return KnowledgeDomainListResponse(
        items=[KnowledgeDomainResponse.from_domain(domain) for domain in domains]
    )


@router.post(
    "",
    response_model=KnowledgeDomainResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a knowledge domain",
    description="Create a new knowledge domain. Names must be unique (case-insensitive).",
    responses=_ERROR_RESPONSES,
)
def create_knowledge_domain(
    body: KnowledgeDomainCreateRequest,
    service: KnowledgeDomainService = Depends(get_knowledge_domain_service),
    current_user: User = Depends(require_permission(Permission.KNOWLEDGE_MANAGE)),
) -> KnowledgeDomainResponse:
    """Create a knowledge domain."""
    domain = service.create_domain(
        name=body.name,
        description=body.description,
    )
    log_with_fields(
        logger,
        logging.INFO,
        "Knowledge domain created via API",
        domain_id=str(domain.id),
        domain_name=domain.name,
        user_id=str(current_user.id),
    )
    return KnowledgeDomainResponse.from_domain(domain)
