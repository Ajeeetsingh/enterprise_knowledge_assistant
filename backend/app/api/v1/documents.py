"""Document management API endpoints."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.auth.authorization import require_role
from app.core.logging import get_logger, log_with_fields
from app.db.models import User
from app.db.repositories.document_repository import DocumentRepository
from app.dependencies import get_document_repository, get_document_service_dep
from app.documents.status import DocumentStatus
from app.ingestion.supported_types import EXTENSION_TO_MIME
from app.mappers.documents import (
    map_to_detail_response,
    map_to_lifecycle_response,
    map_to_paginated_response,
    map_to_upload_response,
)
from app.schemas.documents import (
    DEFAULT_LIST_LIMIT,
    DocumentDetailResponse,
    DocumentLifecycleResponse,
    DocumentUploadResponse,
    PaginatedDocumentResponse,
)
from app.schemas.errors import ErrorResponse
from app.services.document_service import DocumentService

router = APIRouter()
logger = get_logger(__name__)

_DOCUMENT_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid authentication token.",
    },
    403: {
        "model": ErrorResponse,
        "description": "Authenticated user lacks permission to manage documents.",
    },
    404: {
        "model": ErrorResponse,
        "description": "Document not found.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Invalid upload or unsupported document format.",
    },
    500: {
        "model": ErrorResponse,
        "description": "Document ingestion failed.",
    },
    503: {
        "model": ErrorResponse,
        "description": "Document service is temporarily unavailable.",
    },
}


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _resolve_content_type(filename: str, declared_type: str | None) -> str:
    if declared_type and declared_type != "application/octet-stream":
        return declared_type
    ext = Path(filename).suffix.lower()
    return EXTENSION_TO_MIME.get(ext, declared_type or "application/octet-stream")


def _log_operation_success(
    *,
    operation: str,
    user_id: str,
    start: float,
    document_id: str | None = None,
    filename: str | None = None,
) -> None:
    fields: dict[str, object] = {
        "operation": operation,
        "user_id": user_id,
        "status": "success",
        "duration_ms": _elapsed_ms(start),
    }
    if document_id is not None:
        fields["document_id"] = document_id
    if filename is not None:
        fields["filename"] = filename
    log_with_fields(logger, logging.INFO, "Document operation completed", **fields)


@router.get(
    "",
    response_model=PaginatedDocumentResponse,
    summary="List document metadata",
    description=(
        "Return a paginated list of document metadata records. "
        "Supports optional filtering by filename, status, and uploader. "
        "Only administrators may access document metadata."
    ),
    responses=_DOCUMENT_ERROR_RESPONSES,
)
def list_documents(
    limit: int = Query(
        DEFAULT_LIST_LIMIT,
        ge=1,
        le=100,
        description="Maximum number of documents to return.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of documents to skip before returning results.",
    ),
    filename: str | None = Query(
        None,
        description="Optional case-insensitive filename filter (partial match).",
        examples=["handbook"],
    ),
    status: DocumentStatus | None = Query(
        None,
        description="Optional lifecycle status filter.",
    ),
    uploaded_by: uuid.UUID | None = Query(
        None,
        description="Optional filter for documents uploaded by a specific user.",
    ),
    current_user: User = Depends(require_role("Admin")),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
) -> PaginatedDocumentResponse:
    """Return paginated document metadata."""
    start = time.perf_counter()
    user_id = str(current_user.id)

    documents, total = document_service.list_documents(
        repository,
        limit=limit,
        offset=offset,
        filename=filename,
        status=status,
        uploaded_by=uploaded_by,
    )

    _log_operation_success(operation="list_documents", user_id=user_id, start=start)
    return map_to_paginated_response(
        documents,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get document metadata",
    description=(
        "Return metadata for a single document by ID. "
        "File contents are not included. Only administrators may access."
    ),
    responses=_DOCUMENT_ERROR_RESPONSES,
)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("Admin")),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentDetailResponse:
    """Return metadata for a single document."""
    start = time.perf_counter()
    user_id = str(current_user.id)

    document = document_service.get_document(repository, document_id)

    _log_operation_success(
        operation="get_document",
        user_id=user_id,
        document_id=str(document_id),
        start=start,
    )
    return map_to_detail_response(document)


@router.delete(
    "/{document_id}",
    response_model=DocumentLifecycleResponse,
    summary="Delete a document",
    description=(
        "Remove a document from the knowledge base. Deletes indexed vectors, "
        "removes the stored file, and marks metadata as deleted. "
        "Only administrators may delete documents. "
        "Deleting an already-deleted document is idempotent."
    ),
    responses=_DOCUMENT_ERROR_RESPONSES,
)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_role("Admin")),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentLifecycleResponse:
    """Delete a document and remove it from searchable knowledge."""
    start = time.perf_counter()
    user_id = str(current_user.id)

    result = document_service.delete_document(
        repository,
        document_id,
        deleted_by=current_user.id,
    )

    _log_operation_success(
        operation="delete_document",
        user_id=user_id,
        document_id=str(document_id),
        start=start,
    )
    return map_to_lifecycle_response(result)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload an enterprise document",
    description=(
        "Upload a supported document for ingestion into the knowledge base. "
        "Supported formats: PDF, DOCX, TXT, CSV, JSON, and XLSX. "
        "Only administrators may upload documents."
    ),
    responses=_DOCUMENT_ERROR_RESPONSES,
)
def upload_document(
    file: UploadFile = File(
        ...,
        description="Enterprise document file to ingest into the knowledge base.",
    ),
    current_user: User = Depends(require_role("Admin")),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentUploadResponse:
    """Accept a document upload and return its lifecycle status."""
    start = time.perf_counter()
    user_id = str(current_user.id)
    filename = file.filename or ""
    content = file.file.read()
    content_type = _resolve_content_type(filename, file.content_type)

    result = document_service.upload_document(
        repository,
        filename=filename,
        content_type=content_type,
        content=content,
        uploaded_by=current_user.id,
    )

    _log_operation_success(
        operation="upload_document",
        user_id=user_id,
        document_id=result.document_id,
        filename=result.filename,
        start=start,
    )
    return map_to_upload_response(result)
