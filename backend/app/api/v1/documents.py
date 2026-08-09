"""Document management API endpoints."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from urllib.parse import quote

from app.audit.service import AuditService
from app.auth.dependencies import (
    get_user_system_roles,
    require_document_access,
    require_permission,
)
from app.auth.permissions import Permission
from app.auth.role_permissions import SystemRole
from app.core.rate_limit import enforce_rate_limit
from app.core.request_utils import client_ip as _client_ip
from app.db.models import User
from app.db.models.document import Document
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository
from app.dependencies import (
    get_audit_service,
    get_document_repository,
    get_document_service_dep,
    get_knowledge_domain_repository,
)
from app.documents.status import DocumentStatus
from app.ingestion.supported_types import EXTENSION_TO_MIME, MAX_FILE_SIZE_BYTES
from app.mappers.documents import (
    map_to_detail_response,
    map_to_lifecycle_response,
    map_to_paginated_response,
    map_to_summary_response,
    map_to_upload_response,
)
from app.schemas.documents import (
    DEFAULT_LIST_LIMIT,
    DocumentDetailResponse,
    DocumentDomainUpdateRequest,
    DocumentLifecycleResponse,
    DocumentSummaryResponse,
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
    409: {
        "model": ErrorResponse,
        "description": (
            "Document content already exists (DUPLICATE_DOCUMENT) "
            "or filename conflicts with different content."
        ),
    },
    413: {
        "model": ErrorResponse,
        "description": "Uploaded file exceeds the maximum allowed size.",
    },
    422: {
        "model": ErrorResponse,
        "description": "Invalid upload or unsupported document format.",
    },
    429: {
        "model": ErrorResponse,
        "description": "Too many upload requests.",
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


def _resolve_content_type(filename: str, declared_type: str | None = None) -> str:
    """Derive MIME type from the file extension only (ignore client claim)."""
    del declared_type  # Client Content-Type is untrusted.
    ext = Path(filename).suffix.lower()
    return EXTENSION_TO_MIME.get(ext, "application/octet-stream")


def _sanitize_upload_filename(filename: str) -> str:
    """Keep only the basename and strip path / control characters."""
    name = Path(filename or "").name
    cleaned = "".join(
        ch for ch in name if ch.isprintable() and ch not in '<>:"|?*\r\n\x00'
    ).strip()
    if not cleaned or cleaned in {".", ".."}:
        return "upload.bin"
    return cleaned


def _content_disposition(disposition: str, filename: str) -> str:
    """Build a safe Content-Disposition header value."""
    safe = (
        filename.replace('"', "")
        .replace("\r", "")
        .replace("\n", "")
        .replace("\\", "")
    )
    ascii_fallback = "".join(ch if ord(ch) < 128 else "_" for ch in safe) or "download"
    return (
        f"{disposition}; filename=\"{ascii_fallback}\"; "
        f"filename*=UTF-8''{quote(safe)}"
    )


def _is_document_admin(user: User) -> bool:
    return user.is_superuser or SystemRole.ADMIN in get_user_system_roles(user)


def _read_upload_bytes(request: Request, file: UploadFile) -> bytes:
    """Read upload content with an early size cap to avoid unbounded buffering."""
    content_length = request.headers.get("content-length")
    if content_length is not None and content_length.isdigit():
        # multipart overhead means Content-Length can exceed the file size;
        # still reject clearly oversized requests early.
        if int(content_length) > MAX_FILE_SIZE_BYTES + (1024 * 1024):
            raise HTTPException(
                status_code=413,
                detail="File exceeds the maximum allowed size of 50 MB.",
            )

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = file.file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the maximum allowed size of 50 MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)

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
    domain_id: uuid.UUID | None = Query(
        None,
        description=(
            "Optional Knowledge Domain filter. When set, only documents belonging "
            "to that domain are returned (legacy null-domain documents are excluded)."
        ),
    ),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_READ)),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
    domain_repository: KnowledgeDomainRepository = Depends(
        get_knowledge_domain_repository
    ),
) -> PaginatedDocumentResponse:
    """Return paginated document metadata visible to the caller."""
    if status == DocumentStatus.DELETED and not _is_document_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can list deleted documents.",
        )

    if domain_id is not None and domain_repository.get_by_id(domain_id) is None:
        raise HTTPException(
            status_code=422,
            detail="Knowledge domain not found.",
        )

    documents, total = document_service.list_documents(
        repository,
        limit=limit,
        offset=offset,
        filename=filename,
        status=status,
        uploaded_by=uploaded_by,
        domain_id=domain_id,
        viewer=current_user,
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
            "Content-Disposition": _content_disposition(disposition, filename),
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/{document_id}/domain",
    response_model=DocumentSummaryResponse,
    summary="Update document Knowledge Domain",
    description=(
        "Assign or clear the Knowledge Domain for an existing document. "
        "Requires administrator privileges, document update permission, "
        "and document-level access. Pass ``domain_id: null`` to mark the "
        "document as uncategorized."
    ),
    responses=_DOCUMENT_ERROR_RESPONSES,
)
def update_document_domain(
    document_id: uuid.UUID,
    body: DocumentDomainUpdateRequest,
    current_user: User = Depends(require_permission(Permission.DOCUMENT_UPDATE)),
    document: Document = Depends(require_document_access("update")),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
    domain_repository: KnowledgeDomainRepository = Depends(
        get_knowledge_domain_repository
    ),
) -> DocumentSummaryResponse:
    """Persist a Knowledge Domain assignment for an existing document."""
    if not _is_document_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can change a document's knowledge domain.",
        )

    updated = document_service.update_document_domain(
        repository,
        document,
        domain_id=body.domain_id,
        domain_repository=domain_repository,
    )
    return map_to_summary_response(updated)


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
    domain_id: uuid.UUID = Form(
        ...,
        description="Knowledge Domain ID assigned to the uploaded document.",
    ),
    current_user: User = Depends(require_permission(Permission.DOCUMENT_CREATE)),
    document_service: DocumentService = Depends(get_document_service_dep),
    repository: DocumentRepository = Depends(get_document_repository),
    domain_repository: KnowledgeDomainRepository = Depends(
        get_knowledge_domain_repository
    ),
    audit_service: PersistedAuditService = Depends(get_audit_service),
) -> DocumentUploadResponse:
    """Accept a document upload and return its lifecycle status."""
    enforce_rate_limit(
        request,
        bucket="document-upload",
        max_calls=20,
        window_seconds=3600,
        detail="Too many uploads. Please try again later.",
    )

    user_id = str(current_user.id)
    filename = _sanitize_upload_filename(file.filename or "")
    content = _read_upload_bytes(request, file)
    content_type = _resolve_content_type(filename)
    started_at = time.perf_counter()

    logger.info(
        "upload_lifecycle state=Uploading filename=%s bytes=%d user_id=%s domain_id=%s",
        filename,
        len(content),
        user_id,
        domain_id,
    )

    result = document_service.upload_document(
        repository,
        filename=filename,
        content_type=content_type,
        content=content,
        uploaded_by=current_user.id,
        requesting_user=current_user,
        domain_id=domain_id,
        domain_repository=domain_repository,
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
