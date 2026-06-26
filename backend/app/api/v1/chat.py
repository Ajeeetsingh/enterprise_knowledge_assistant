"""Authenticated chat API endpoints."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, Request

from app.audit.service import AuditService
from app.auth.retrieval_authorization import (
    EMPTY_RETRIEVAL_MESSAGE,
    RetrievalAuthorizationService,
)
from app.auth.security import get_current_user
from app.core.exceptions import (
    AuthorizationError,
    ConversationAccessDeniedError,
    RagInitializationError,
    RagRetrievalError,
)
from app.core.logging import get_logger, log_with_fields
from app.db.models import User
from app.db.repositories.document_repository import DocumentRepository
from app.dependencies import (
    get_audit_service,
    get_conversation_chat_service,
    get_document_repository,
    get_rag_service_dep,
)
from app.mappers.chat import map_chat_result_to_answer_response
from app.rag.types import Citation, QueryResponse
from app.schemas.chat import AnswerResponse, ChatAskRequest
from app.schemas.errors import ErrorResponse
from app.services import chat_audit_integration, security_audit_integration
from app.services.audit_service import AuditService as PersistedAuditService
from app.services.conversation_chat_service import ConversationChatService
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
        "description": "Authenticated user has no assigned role or does not own the conversation.",
    },
    404: {
        "model": ErrorResponse,
        "description": "Conversation not found.",
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


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


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
    summary="Ask a knowledge question in a conversation",
    description=(
        "Submit a natural-language question within an existing conversation. "
        "Recent conversation history is assembled into a context-aware query "
        "before retrieval. Returns a grounded answer with citations and a "
        "confidence score."
    ),
    responses=_CHAT_ERROR_RESPONSES,
)
def ask_question(
    body: ChatAskRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    chat_service: ConversationChatService = Depends(get_conversation_chat_service),
    rag_service: RagService = Depends(get_rag_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
    audit_service: PersistedAuditService = Depends(get_audit_service),
) -> AnswerResponse:
    """Submit a conversation-aware enterprise question and receive a RAG answer."""
    start = time.perf_counter()
    user_id = str(current_user.id)
    query_id = str(uuid.uuid4())
    ip_address = _client_ip(request)
    user_agent = request.headers.get("User-Agent")
    clean_question = body.question.strip()

    chat_audit_integration.record_question_asked(
        audit_service,
        user_id=current_user.id,
        conversation_id=body.conversation_id,
        query_length=len(clean_question),
        ip_address=ip_address,
        user_agent=user_agent,
    )

    try:
        role_name = _primary_role_name(current_user)
    except AuthorizationError as exc:
        security_audit_integration.record_permission_denied(
            audit_service,
            user_id=current_user.id,
            required_permission="role:assigned",
            resource=request.url.path,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise exc

    authorized_sources = _get_authorized_sources(current_user, repository, query_id)

    try:
        result = chat_service.ask_question(
            current_user,
            body.conversation_id,
            body.question,
            role_name,
            rag_service,
            authorized_sources,
        )
    except (RagRetrievalError, RagInitializationError) as exc:
        chat_audit_integration.record_retrieval_failed(
            audit_service,
            user_id=current_user.id,
            conversation_id=body.conversation_id,
            reason=exc.public_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise
    except ConversationAccessDeniedError as exc:
        security_audit_integration.record_permission_denied(
            audit_service,
            user_id=current_user.id,
            required_permission="conversation:owner",
            resource=request.url.path,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        raise exc

    chat_audit_integration.record_answer_generated(
        audit_service,
        user_id=current_user.id,
        conversation_id=result.conversation_id,
        citation_count=len(result.citations),
        confidence_score=result.confidence_score,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    AuditService.record(
        AuditService.rag_query(user_id=user_id, query_id=query_id)
    )
    _log_chat_success(user_id, start)
    return map_chat_result_to_answer_response(result)
