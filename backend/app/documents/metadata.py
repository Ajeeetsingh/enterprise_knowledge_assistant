"""Document metadata structures for ingestion and future persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class IndexingStatus(StrEnum):
    """Lifecycle status of a document in the ingestion pipeline."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Metadata describing an enterprise document.

    Designed for future persistence in PostgreSQL without coupling to ORM models.
    """

    filename: str
    content_type: str
    checksum: str
    uploaded_at: datetime
    indexing_status: IndexingStatus
    document_id: str = field(default_factory=lambda: str(uuid4()))
    storage_path: str | None = None
    category: str | None = None
    tenant_id: str | None = None

    @classmethod
    def create_pending(
        cls,
        *,
        filename: str,
        content_type: str,
        checksum: str,
        storage_path: str | None = None,
        tenant_id: str | None = None,
    ) -> DocumentMetadata:
        """Create metadata for a newly accepted document awaiting full indexing."""
        return cls(
            filename=filename,
            content_type=content_type,
            checksum=checksum,
            uploaded_at=datetime.now(UTC),
            indexing_status=IndexingStatus.PENDING,
            storage_path=storage_path,
            tenant_id=tenant_id,
        )
