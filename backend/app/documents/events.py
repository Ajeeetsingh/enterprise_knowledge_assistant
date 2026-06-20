"""Internal domain events for document lifecycle operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class DocumentLifecycleEvent:
    """Base lifecycle event for audit-ready, in-process dispatch.

    Future modules (audit, notifications, async workers) can subscribe to
    these events without modifying ``DocumentService``.
    """

    document_id: str
    user_id: str
    operation: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    checksum: str | None = None


@dataclass(frozen=True)
class DocumentUploaded(DocumentLifecycleEvent):
    """Emitted when a document is successfully uploaded and ingested."""

    operation: str = field(default="uploaded", init=False)


@dataclass(frozen=True)
class DocumentIndexed(DocumentLifecycleEvent):
    """Emitted when a document becomes searchable in the vector index."""

    operation: str = field(default="indexed", init=False)


@dataclass(frozen=True)
class DocumentDeleted(DocumentLifecycleEvent):
    """Emitted when a document is removed from the knowledge base."""

    operation: str = field(default="deleted", init=False)


@dataclass(frozen=True)
class DocumentReindexed(DocumentLifecycleEvent):
    """Reserved for future re-index operations."""

    operation: str = field(default="reindexed", init=False)


@dataclass(frozen=True)
class DuplicateDetected(DocumentLifecycleEvent):
    """Emitted when an upload matches an existing document's content identity."""

    operation: str = field(default="duplicate_detected", init=False)


@dataclass(frozen=True)
class DocumentVersionCreated(DocumentLifecycleEvent):
    """Reserved for future document versioning."""

    operation: str = field(default="version_created", init=False)


@dataclass(frozen=True)
class DocumentReplaced(DocumentLifecycleEvent):
    """Reserved for future document replacement."""

    operation: str = field(default="replaced", init=False)


@dataclass(frozen=True)
class DocumentProcessingStarted(DocumentLifecycleEvent):
    """Emitted when document ingestion processing begins."""

    operation: str = field(default="processing_started", init=False)
    stage: str | None = None


@dataclass(frozen=True)
class DocumentProcessingCompleted(DocumentLifecycleEvent):
    """Emitted when document ingestion processing completes successfully."""

    operation: str = field(default="processing_completed", init=False)
    total_duration_ms: float | None = None


@dataclass(frozen=True)
class DocumentProcessingFailed(DocumentLifecycleEvent):
    """Emitted when document ingestion processing fails."""

    operation: str = field(default="processing_failed", init=False)
    stage: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class DocumentRetryScheduled(DocumentLifecycleEvent):
    """Emitted when a failed document is marked for retry."""

    operation: str = field(default="retry_scheduled", init=False)


@dataclass(frozen=True)
class DocumentRetryCompleted(DocumentLifecycleEvent):
    """Emitted when a document retry completes successfully."""

    operation: str = field(default="retry_completed", init=False)
