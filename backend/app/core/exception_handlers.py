"""Global FastAPI exception handlers."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import DuplicateDocumentError, ServiceError
from app.core.logging import get_logger, log_with_fields
from app.schemas.errors import ErrorResponse

logger = get_logger(__name__)


def _request_context(request: Request) -> dict[str, str | None]:
    """Extract safe request metadata for structured error logging."""
    return {
        "path": request.url.path,
        "user_id": getattr(request.state, "user_id", None),
        "request_id": request.headers.get("X-Request-ID"),
    }


def _log_exception(
    request: Request,
    exc: Exception,
    *,
    level: int = logging.ERROR,
) -> None:
    context = _request_context(request)
    log_with_fields(
        logger,
        level,
        "Request failed",
        exception_type=type(exc).__name__,
        path=context["path"],
        user_id=context["user_id"],
        request_id=context["request_id"],
    )


def _error_response(
    status_code: int,
    detail: str,
    *,
    code: str | None = None,
    existing_document_id: str | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        detail=detail,
        code=code,
        existing_document_id=existing_document_id,
    ).model_dump(mode="json", exclude_none=True)
    return JSONResponse(status_code=status_code, content=payload)


async def service_error_handler(
    request: Request,
    exc: ServiceError,
) -> JSONResponse:
    """Map enterprise service exceptions to consistent ErrorResponse payloads."""
    context = _request_context(request)
    log_with_fields(
        logger,
        logging.ERROR,
        "Request failed",
        exception_type=type(exc).__name__,
        path=context["path"],
        user_id=context["user_id"],
        request_id=context["request_id"],
        internal_message=exc.message,
    )
    existing_document_id = (
        exc.existing_document_id
        if isinstance(exc, DuplicateDocumentError)
        else None
    )
    return _error_response(
        exc.status_code,
        exc.public_message,
        code=exc.code,
        existing_document_id=existing_document_id,
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Map request validation failures to a consistent ErrorResponse."""
    _log_exception(request, exc)
    return _error_response(422, "Invalid request.")


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Log HTTP exceptions and return a consistent ErrorResponse."""
    if exc.status_code >= 500:
        _log_exception(request, exc)
    elif exc.status_code in {401, 403}:
        _log_exception(request, exc, level=logging.WARNING)

    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _error_response(exc.status_code, detail)


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log unexpected errors without leaking internals to clients."""
    _log_exception(request, exc)
    return _error_response(500, "An unexpected error occurred.")


def register_exception_handlers(application: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI application."""
    application.add_exception_handler(ServiceError, service_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
