"""Document lifecycle status and upload result types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.documents.types import IngestionResult


class DocumentStatus(StrEnum):
    """Public document lifecycle states exposed by the Document Management API.

    Designed for future asynchronous ingestion: the same status values apply
    whether processing completes synchronously or is queued for background work.
    """

    UPLOADED = "uploaded"
    VALIDATED = "validated"
    STORED = "stored"
    PROCESSING = "processing"
    INDEXED = "indexed"
    SEARCHABLE = "searchable"
    FAILED = "failed"
    RETRY_PENDING = "retry_pending"
    DELETED = "deleted"


@dataclass(frozen=True)
class DocumentUploadResult:
    """Business result returned by ``DocumentService.upload_document``.

    Hides ingestion pipeline internals from the API layer.
    """

    document_id: str
    filename: str
    status: DocumentStatus
    message: str

    @classmethod
    def from_ingestion(cls, result: IngestionResult) -> DocumentUploadResult:
        """Map a completed ingestion run to a business-oriented upload result."""
        metadata = result.metadata
        if result.indexed:
            status = DocumentStatus.SEARCHABLE
            message = (
                f"Document '{metadata.filename}' uploaded and is now searchable."
            )
        else:
            status = DocumentStatus.STORED
            message = f"Document '{metadata.filename}' stored successfully."

        return cls(
            document_id=metadata.document_id,
            filename=metadata.filename,
            status=status,
            message=message,
        )

    @classmethod
    def from_existing_document(
        cls,
        document: object,
        *,
        message: str | None = None,
    ) -> DocumentUploadResult:
        """Build an upload result referencing an existing document (duplicate path)."""
        filename = document.filename
        status = DocumentStatus(document.status)
        return cls(
            document_id=str(document.id),
            filename=filename,
            status=status,
            message=message
            or f"Document '{filename}' already exists with identical content.",
        )
