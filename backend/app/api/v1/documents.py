"""Document management API endpoints."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from app.audit.service import AuditService
from app.auth.dependencies import require_document_access, require_permission
from app.auth.permissions import Permission
from app.db.models import User
from app.db.models.document import Document
from app.db.repositories.document_repository import DocumentRepository
from app.dependencies import (
    get_audit_service,
    get_document_repository,
    get_document_service_dep,
)
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
from app.services.audit_service import AuditService as PersistedAuditService
from app.services import document_audit_integration

router = APIRouter()

logger = logging.getLogger(__name__)

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


def _resolve_content_type(filename: str, declared_type: str | None) -> str:
    if declared_type and declared_type != "application/octet-stream":
        return declared_type
    ext = Path(filename).suffix.lower()
    return EXTENSION_TO_MIME.get(ext, declared_type or "application/octet-stream")


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.get(
    "",
    response_model=PaginatedDocumentResponse,
    summary="List document metadata",
    description=(
        "Return a paginated list of document metadata records. "
        "Supports optional filtering by filename, status, and uploader. "
        "Only users with document read permission may access document metadata."
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
    current_user: User = Depends(require_permission(Permission.DOCUMENT_READ)),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
) -> PaginatedDocumentResponse:
    """Return paginated document metadata."""
    documents, total = document_service.list_documents(
        repository,
        limit=limit,
        offset=offset,
        filename=filename,
        status=status,
        uploaded_by=uploaded_by,
    )

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
        "File contents are not included. Requires document read permission "
        "and document-level access (visibility, ownership, or role)."
    ),
    responses=_DOCUMENT_ERROR_RESPONSES,
)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.DOCUMENT_READ)),
    document: Document = Depends(require_document_access("read")),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
) -> DocumentDetailResponse:
    """Return metadata for a single document."""
    user_id = str(current_user.id)

    AuditService.record(
        AuditService.document_read(user_id=user_id, document_id=str(document_id))
    )
    return map_to_detail_response(document)


@router.get(
    "/{document_id}/file",
    summary="Download or preview document file",
    description=(
        "Return the stored document bytes for in-app preview or download. "
        "Requires document read permission and document-level access. "
        "Use ``download=true`` to suggest a file download instead of inline preview."
    ),
    responses={
        **_DOCUMENT_ERROR_RESPONSES,
        200: {
            "content": {"application/octet-stream": {}},
            "description": "Raw document file bytes.",
        },
    },
)
def get_document_file(
    document_id: uuid.UUID,
    download: bool = Query(
        False,
        description="When true, Content-Disposition is attachment instead of inline.",
    ),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_READ)),
    document: Document = Depends(require_document_access("read")),
    document_service: DocumentService = Depends(get_document_service_dep),
) -> Response:
    """Stream the stored document file for preview or download."""
    user_id = str(current_user.id)
    content, content_type, filename = document_service.read_document_file(document)

    disposition = "attachment" if download else "inline"
    AuditService.record(
        AuditService.document_read(user_id=user_id, document_id=str(document_id))
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.delete(
    "/{document_id}",
    response_model=DocumentLifecycleResponse,
    summary="Delete a document",
    description=(
        "Remove a document from the knowledge base. Deletes indexed vectors, "
        "removes the stored file, and marks metadata as deleted. "
        "Requires document delete permission and document-level access. "
        "Deleting an already-deleted document is idempotent."
    ),
    responses=_DOCUMENT_ERROR_RESPONSES,
)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_permission(Permission.DOCUMENT_DELETE)),
    document: Document = Depends(require_document_access("delete")),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
    audit_service: PersistedAuditService = Depends(get_audit_service),
) -> DocumentLifecycleResponse:
    """Delete a document and remove it from searchable knowledge."""
    user_id = str(current_user.id)

    result = document_service.delete_document(
        repository,
        document_id,
        deleted_by=current_user.id,
    )

    AuditService.record(
        AuditService.document_deleted(user_id=user_id, document_id=str(document_id))
    )
    document_audit_integration.record_document_deleted_from_document(
        audit_service,
        user_id=current_user.id,
        document=document,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return map_to_lifecycle_response(result)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload an enterprise document",
    description=(
        "Upload a supported document for ingestion into the knowledge base. "
        "Supported formats: PDF, DOCX, TXT, CSV, JSON, and XLSX. "
        "Only users with document create permission may upload documents."
    ),
    responses=_DOCUMENT_ERROR_RESPONSES,
)
def upload_document(
    request: Request,
    file: UploadFile = File(
        ...,
        description="Enterprise document file to ingest into the knowledge base.",
    ),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_CREATE)),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
    audit_service: PersistedAuditService = Depends(get_audit_service),
) -> DocumentUploadResponse:
    """Accept a document upload and return its lifecycle status."""
    user_id = str(current_user.id)
    filename = file.filename or ""
    content = file.file.read()
    content_type = _resolve_content_type(filename, file.content_type)
    started_at = time.perf_counter()

    logger.info(
        "upload_lifecycle state=Uploading filename=%s bytes=%d user_id=%s",
        filename,
        len(content),
        user_id,
    )

    result = document_service.upload_document(
        repository,
        filename=filename,
        content_type=content_type,
        content=content,
        uploaded_by=current_user.id,
    )

    elapsed_s = time.perf_counter() - started_at
    logger.info(
        "upload_lifecycle state=%s document_id=%s filename=%s elapsed_s=%.2f message=%s",
        result.status.value,
        result.document_id,
        result.filename,
        elapsed_s,
        result.message,
    )

    AuditService.record(
        AuditService.document_created(
            user_id=user_id,
            document_id=result.document_id,
            filename=result.filename,
        )
    )

    uploaded_document = repository.get_by_id(uuid.UUID(result.document_id))
    if uploaded_document is not None:
        document_audit_integration.record_document_uploaded_from_document(
            audit_service,
            user_id=current_user.id,
            document=uploaded_document,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
    else:
        document_audit_integration.record_document_uploaded(
            audit_service,
            user_id=current_user.id,
            document_id=uuid.UUID(result.document_id),
            document_name=result.filename,
            document_type=content_type,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )

    return map_to_upload_response(result)
