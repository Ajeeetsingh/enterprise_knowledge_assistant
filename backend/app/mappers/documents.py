"""Map document entities to public API models."""

from __future__ import annotations

from typing import Protocol

from app.documents.lifecycle import DocumentLifecycleResult
from app.documents.integrity import DocumentIntegrityResult
from app.documents.status import DocumentUploadResult
from app.schemas.documents import (
    DocumentDetailResponse,
    DocumentIntegrityResponse,
    DocumentLifecycleResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
    PaginatedDocumentResponse,
)


class _DocumentLike(Protocol):
    id: object
    filename: str
    content_type: str
    file_size: int
    checksum: str
    status: str
    uploaded_at: object
    uploaded_by: object


def map_to_upload_response(result: DocumentUploadResult) -> DocumentUploadResponse:
    """Convert a business upload result into the public API contract."""
    return DocumentUploadResponse(
        document_id=result.document_id,
        filename=result.filename,
        status=result.status,
        message=result.message,
    )


def map_to_summary_response(document: _DocumentLike) -> DocumentSummaryResponse:
    """Convert a document entity into a summary API response."""
    domain_id = getattr(document, "domain_id", None)
    knowledge_domain = getattr(document, "knowledge_domain", None)
    domain_name = None
    if knowledge_domain is not None:
        domain_name = getattr(knowledge_domain, "name", None)

    return DocumentSummaryResponse(
        document_id=str(document.id),
        filename=document.filename,
        status=document.status,
        uploaded_at=document.uploaded_at,
        uploaded_by=str(document.uploaded_by),
        domain_id=domain_id,
        domain_name=domain_name,
    )


def map_to_detail_response(document: _DocumentLike) -> DocumentDetailResponse:
    """Convert a document entity into a detail API response."""
    return DocumentDetailResponse(
        document_id=str(document.id),
        filename=document.filename,
        content_type=document.content_type,
        file_size=document.file_size,
        checksum=document.checksum,
        status=document.status,
        uploaded_at=document.uploaded_at,
        uploaded_by=str(document.uploaded_by),
    )


def map_to_paginated_response(
    documents: list[_DocumentLike],
    *,
    total: int,
    limit: int,
    offset: int,
) -> PaginatedDocumentResponse:
    """Convert a page of document entities into a paginated API response."""
    return PaginatedDocumentResponse(
        items=[map_to_summary_response(document) for document in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


def map_to_lifecycle_response(
    result: DocumentLifecycleResult,
) -> DocumentLifecycleResponse:
    """Convert a business lifecycle result into the public API contract."""
    return DocumentLifecycleResponse(
        document_id=result.document_id,
        status=result.status,
        message=result.message,
    )


def map_to_integrity_response(
    result: DocumentIntegrityResult,
) -> DocumentIntegrityResponse:
    """Convert a business integrity result into the public API contract."""
    return DocumentIntegrityResponse(
        decision=result.decision.value,
        checksum=result.checksum,
        filename=result.filename,
        message=result.message,
        document_id=result.document_id,
        existing_filename=result.existing_filename,
    )
