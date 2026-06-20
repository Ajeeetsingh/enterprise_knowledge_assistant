"""Authenticated chat API endpoints."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.core.exceptions import AuthorizationError
from app.core.logging import get_logger, log_with_fields
from app.db.models import User
from app.dependencies import get_rag_service_dep
from app.mappers import map_to_answer_response
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
) -> AnswerResponse:
    """Submit an enterprise question and receive a RAG-generated answer."""
    start = time.perf_counter()
    user_id = str(current_user.id)
    role_name = _primary_role_name(current_user)

    query_response = rag_service.answer_question(body.question, role_name)

    _log_chat_success(user_id, start)
    return map_to_answer_response(query_response)
