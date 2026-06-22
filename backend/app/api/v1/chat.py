"""Authenticated chat API endpoints."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends

from app.audit.service import AuditService
from app.auth.retrieval_authorization import (
    EMPTY_RETRIEVAL_MESSAGE,
    RetrievalAuthorizationService,
)
from app.auth.security import get_current_user
from app.core.exceptions import AuthorizationError
from app.core.logging import get_logger, log_with_fields
from app.db.models import User
from app.db.repositories.document_repository import DocumentRepository
from app.dependencies import get_document_repository, get_rag_service_dep
from app.mappers import map_to_answer_response
from app.rag.types import Citation, QueryResponse
from app.schemas.chat import AnswerResponse, ChatAskRequest
from app.schemas.errors import ErrorResponse
from app.services.rag_service import RagService

router = APIRouter()
logger = get_logger(__name__)

_ROLE_PRIORITY: dict[str, int] = {
    "Admin": 0,
    "HR": 1,
    "Finance": 2,
    "Employee": 3,
}

_CHAT_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Authenticated user has no assigned role.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Request validation failed.",
    },
    503: {
        "model": ErrorResponse,
        "description": "Knowledge service is temporarily unavailable.",
    },
    500: {
        "model": ErrorResponse,
        "description": "Failed to process the knowledge request.",
    },
}


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _log_chat_success(user_id: str, start: float) -> None:
    log_with_fields(
        logger,
        logging.INFO,
        "Chat ask completed",
        user_id=user_id,
        status="success",
        duration_ms=_elapsed_ms(start),
    )


def _primary_role_name(user: User) -> str:
    """Return the highest-priority assigned role name for RAG authorization."""
    if not user.roles:
        raise AuthorizationError()
    primary_role = min(
        user.roles,
        key=lambda role: _ROLE_PRIORITY.get(role.name, 99),
    )
    return primary_role.name


def _empty_authorized_response(query: str, role: str) -> QueryResponse:
    """Build a QueryResponse for when no authorized sources remain."""
    return QueryResponse(
        query=query,
        role=role,
        routed_category="",
        route_confidence=0.0,
        answer=EMPTY_RETRIEVAL_MESSAGE,
        sources_used=[],
        citations=[],
        confidence_score=0.0,
        access_granted=True,
        message=EMPTY_RETRIEVAL_MESSAGE,
    )


def _get_authorized_sources(
    user: User,
    repository: DocumentRepository,
    query_id: str,
) -> frozenset[str] | None:
    """Return the authorized document source set for *user*.

    Fetches all non-deleted searchable documents from the repository in a
    single batch query, applies ``DocumentAuthorizationService`` rules, and
    returns the set of authorized filenames.

    Returns ``None`` when the repository is unavailable (graceful fallback
    to category-based RBAC only) so that a transient DB error does not
    silently deny retrieval — consistent with the fail-open-for-legacy-docs
    policy for filesystem-only sources.

    In practice the repository is always available during a normal request.
    """
    try:
        # Fetch all searchable documents in one query.  For large corpora a
        # paginated approach or pre-computed authorized-set cache would be
        # preferred (Phase 5.6+ performance work).
        all_docs, _ = repository.list(limit=10_000, offset=0)
        candidate_sources = frozenset(doc.filename for doc in all_docs)

        authorized = RetrievalAuthorizationService.get_authorized_sources(
            user,
            candidate_sources,
            repository,
            query_id=query_id,
        )

        # Emit audit event when authorization removed any candidate sources.
        candidate_count = len(candidate_sources)
        authorized_count = len(authorized)
        filtered_count = candidate_count - authorized_count
        if filtered_count > 0:
            AuditService.record(
                AuditService.rag_retrieval_filtered(
                    user_id=str(user.id),
                    query_id=query_id,
                    candidate_count=candidate_count,
                    authorized_count=authorized_count,
                    filtered_count=filtered_count,
                )
            )

        return authorized
    except Exception:
        # Graceful fallback — do not let a DB error block the query.
        log_with_fields(
            logger,
            logging.WARNING,
            "Retrieval authorization source lookup failed; falling back to category RBAC",
            user_id=str(user.id),
            query_id=query_id,
        )
        return None


@router.post(
    "/ask",
    response_model=AnswerResponse,
    summary="Ask a knowledge question",
    description=(
        "Submit a natural-language question about enterprise policies or documents. "
        "Returns a grounded answer with citations and a confidence score."
    ),
    responses=_CHAT_ERROR_RESPONSES,
)
def ask_question(
    body: ChatAskRequest,
    current_user: User = Depends(get_current_user),
    rag_service: RagService = Depends(get_rag_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
) -> AnswerResponse:
    """Submit an enterprise question and receive a RAG-generated answer."""
    start = time.perf_counter()
    user_id = str(current_user.id)
    query_id = str(uuid.uuid4())
    role_name = _primary_role_name(current_user)

    # Compute authorized document sources (Phase 5.5 document-level auth).
    authorized_sources = _get_authorized_sources(current_user, repository, query_id)

    query_response = rag_service.answer_question(
        body.question,
        role_name,
        authorized_sources,
    )

    AuditService.record(
        AuditService.rag_query(user_id=user_id, query_id=query_id)
    )
    _log_chat_success(user_id, start)
    return map_to_answer_response(query_response)
