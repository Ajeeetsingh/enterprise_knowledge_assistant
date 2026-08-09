"""Pydantic models for the document management API public contract."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.documents.status import DocumentStatus

DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 100


class DocumentUploadResponse(BaseModel):
    """Public API response after a successful document upload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "filename": "employee_handbook.pdf",
                    "status": "searchable",
                    "message": (
                        "Document 'employee_handbook.pdf' uploaded "
                        "and is now searchable."
                    ),
                }
            ]
        }
    )

    document_id: str = Field(
        ...,
        description="Unique identifier for the uploaded document.",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    filename: str = Field(
        ...,
        description="Original filename of the uploaded document.",
        examples=["employee_handbook.pdf"],
    )
    status: DocumentStatus = Field(
        ...,
        description=(
            "Current lifecycle status of the document. "
            "Designed to support both synchronous and future asynchronous ingestion."
        ),
        examples=[DocumentStatus.SEARCHABLE],
    )
    message: str = Field(
        ...,
        description="Human-readable summary of the upload outcome.",
        examples=[
            "Document 'employee_handbook.pdf' uploaded and is now searchable."
        ],
    )


class DocumentSummaryResponse(BaseModel):
    """Summary metadata for a document in list responses."""

    document_id: str = Field(
        ...,
        description="Unique identifier for the document.",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    filename: str = Field(
        ...,
        description="Original filename of the uploaded document.",
        examples=["employee_handbook.pdf"],
    )
    status: DocumentStatus = Field(
        ...,
        description="Current lifecycle status of the document.",
        examples=[DocumentStatus.SEARCHABLE],
    )
    uploaded_at: datetime = Field(
        ...,
        description="UTC timestamp when the document was uploaded.",
    )
    uploaded_by: str = Field(
        ...,
        description="UUID of the user who uploaded the document.",
        examples=["f47ac10b-58cc-4372-a567-0e02b2c3d479"],
    )
    domain_id: uuid.UUID | None = Field(
        default=None,
        description="Knowledge Domain ID, or null for legacy uncategorized documents.",
    )
    domain_name: str | None = Field(
        default=None,
        description=(
            "Knowledge Domain display name. Null when the document has no domain "
            "(legacy / uncategorized)."
        ),
        examples=["Finance"],
    )


class DocumentDomainUpdateRequest(BaseModel):
    """Request body for assigning or clearing a document's Knowledge Domain."""

    domain_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Knowledge Domain ID to assign. Null clears the assignment "
            "(document becomes uncategorized)."
        ),
    )


class DocumentDetailResponse(BaseModel):
    """Detailed metadata for a single document."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "filename": "employee_handbook.pdf",
                    "content_type": "application/pdf",
                    "file_size": 1048576,
                    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "status": "searchable",
                    "uploaded_at": "2026-06-20T10:30:00Z",
                    "uploaded_by": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                }
            ]
        }
    )

    document_id: str = Field(
        ...,
        description="Unique identifier for the document.",
    )
    filename: str = Field(
        ...,
        description="Original filename of the uploaded document.",
    )
    content_type: str = Field(
        ...,
        description="MIME type of the uploaded document.",
        examples=["application/pdf"],
    )
    file_size: int = Field(
        ...,
        ge=0,
        description="Size of the uploaded file in bytes.",
        examples=[1048576],
    )
    checksum: str = Field(
        ...,
        description="SHA-256 checksum of the original file.",
    )
    status: DocumentStatus = Field(
        ...,
        description="Current lifecycle status of the document.",
    )
    uploaded_at: datetime = Field(
        ...,
        description="UTC timestamp when the document was uploaded.",
    )
    uploaded_by: str = Field(
        ...,
        description="UUID of the user who uploaded the document.",
    )


class PaginatedDocumentResponse(BaseModel):
    """Paginated list of document metadata records."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "filename": "employee_handbook.pdf",
                            "status": "searchable",
                            "uploaded_at": "2026-06-20T10:30:00Z",
                            "uploaded_by": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                        }
                    ],
                    "total": 1,
                    "limit": DEFAULT_LIST_LIMIT,
                    "offset": 0,
                }
            ]
        }
    )

    items: list[DocumentSummaryResponse] = Field(
        default_factory=list,
        description="Page of document metadata summaries.",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of documents matching the applied filters.",
        examples=[42],
    )
    limit: int = Field(
        ...,
        ge=1,
        le=MAX_LIST_LIMIT,
        description="Maximum number of items returned in this page.",
        examples=[DEFAULT_LIST_LIMIT],
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Number of items skipped before this page.",
        examples=[0],
    )


class DocumentLifecycleResponse(BaseModel):
    """Public API response for document lifecycle operations such as delete."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "status": "deleted",
                    "message": (
                        "Document 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' "
                        "deleted successfully."
                    ),
                }
            ]
        }
    )

    document_id: str = Field(
        ...,
        description="Unique identifier of the affected document.",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    status: DocumentStatus = Field(
        ...,
        description="Resulting lifecycle status after the operation.",
        examples=[DocumentStatus.DELETED],
    )
    message: str = Field(
        ...,
        description="Human-readable summary of the lifecycle outcome.",
        examples=[
            "Document 'a1b2c3d4-e5f6-7890-abcd-ef1234567890' deleted successfully."
        ],
    )


class DocumentIntegrityResponse(BaseModel):
    """Public API response describing an upload integrity evaluation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "decision": "exact_duplicate",
                    "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "filename": "employee_handbook.pdf",
                    "message": (
                        "Document with identical content already exists "
                        "as 'employee_handbook.pdf'."
                    ),
                }
            ]
        }
    )

    decision: str = Field(
        ...,
        description="Integrity policy outcome for the upload request.",
        examples=["exact_duplicate"],
    )
    checksum: str = Field(
        ...,
        description="Content identity checksum computed for the upload.",
    )
    filename: str = Field(
        ...,
        description="Requested upload filename.",
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of the integrity decision.",
    )
    document_id: str | None = Field(
        default=None,
        description="Existing document ID when the decision references a prior upload.",
    )
    existing_filename: str | None = Field(
        default=None,
        description="Filename of the existing document when content is duplicated.",
    )
