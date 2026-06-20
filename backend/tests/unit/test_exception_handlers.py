"""Unit tests for global exception handlers."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.core.exception_handlers import (
    http_exception_handler,
    service_error_handler,
    validation_error_handler,
)
from app.core.exceptions import (
    AuthorizationError,
    DocumentNotFoundError,
    RagInitializationError,
    RagRetrievalError,
)


def _mock_request(
    *,
    path: str = "/api/v1/chat/ask",
    user_id: str | None = "user-123",
    request_id: str | None = None,
) -> MagicMock:
    request = MagicMock()
    request.url.path = path
    request.state.user_id = user_id
    request.headers.get.return_value = request_id
    return request


def test_rag_initialization_error_returns_503() -> None:
    request = _mock_request()
    exc = RagInitializationError("Knowledge base data directory is not available.")

    response = asyncio.run(service_error_handler(request, exc))
    body = json.loads(response.body.decode())

    assert response.status_code == 503
    assert body == {"detail": "Knowledge service is temporarily unavailable."}


def test_rag_retrieval_error_returns_500() -> None:
    request = _mock_request()
    exc = RagRetrievalError("Knowledge retrieval failed.")

    response = asyncio.run(service_error_handler(request, exc))

    assert response.status_code == 500
    assert (
        response.body.decode().count("Failed to process knowledge request.") == 1
    )


def test_authorization_error_returns_403() -> None:
    request = _mock_request()
    exc = AuthorizationError()

    response = asyncio.run(service_error_handler(request, exc))

    assert response.status_code == 403
    assert "User has no assigned role." in response.body.decode()


def test_document_not_found_error_returns_404() -> None:
    request = _mock_request(path="/api/v1/documents/123")
    exc = DocumentNotFoundError("Document not found.")

    response = asyncio.run(service_error_handler(request, exc))
    body = json.loads(response.body.decode())

    assert response.status_code == 404
    assert body == {"detail": "Document not found."}


def test_validation_error_returns_422() -> None:
    request = _mock_request(user_id=None)
    exc = RequestValidationError(errors=[])

    response = asyncio.run(validation_error_handler(request, exc))

    assert response.status_code == 422
    assert "Invalid request." in response.body.decode()


def test_http_exception_preserves_authentication_detail() -> None:
    request = _mock_request(user_id=None)
    exc = HTTPException(status_code=401, detail="Not authenticated.")

    response = asyncio.run(http_exception_handler(request, exc))

    assert response.status_code == 401
    assert "Not authenticated." in response.body.decode()


def test_error_response_does_not_leak_internal_message() -> None:
    request = _mock_request()
    exc = RagInitializationError("postgresql connection timeout at 127.0.0.1")

    response = asyncio.run(service_error_handler(request, exc))
    body = response.body.decode()

    assert "postgresql" not in body
    assert "127.0.0.1" not in body
