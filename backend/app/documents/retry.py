"""Document retry foundation — architecture only, no background workers."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.db.repositories.document_repository import DocumentRepository
from app.documents.dispatcher import LifecycleEventCollector
from app.documents.events import DocumentRetryCompleted, DocumentRetryScheduled
from app.documents.status import DocumentStatus
from app.core.exceptions import DocumentIngestionError, DocumentNotFoundError


@dataclass(frozen=True)
class DocumentRetryResult:
    """Business result from a retry scheduling or execution operation."""

    document_id: str
    status: DocumentStatus
    message: str
    retry_scheduled: bool = False

    @classmethod
    def scheduled(cls, document_id: str) -> DocumentRetryResult:
        return cls(
            document_id=document_id,
            status=DocumentStatus.RETRY_PENDING,
            message=f"Retry scheduled for document '{document_id}'.",
            retry_scheduled=True,
        )

    @classmethod
    def completed(cls, document_id: str, *, final_status: DocumentStatus) -> DocumentRetryResult:
        return cls(
            document_id=document_id,
            status=final_status,
            message=f"Retry completed for document '{document_id}'.",
            retry_scheduled=False,
        )


class DocumentRetryHandler(ABC):
    """Contract for future retryable document processing."""

    @abstractmethod
    def schedule_retry(
        self,
        repository: DocumentRepository,
        document_id: uuid.UUID,
        *,
        user_id: str,
        event_collector: LifecycleEventCollector,
    ) -> DocumentRetryResult:
        """Mark a failed document for retry without executing it."""

    @abstractmethod
    def can_retry(self, status: str) -> bool:
        """Return whether the given document status is eligible for retry."""


class DefaultDocumentRetryHandler(DocumentRetryHandler):
    """Default retry handler — schedules retries in-process, no background queue.

    Future Celery/RabbitMQ workers can implement ``DocumentRetryHandler``
    without changing ``DocumentService``.
    """

    _RETRYABLE_STATUSES = frozenset({
        DocumentStatus.FAILED.value,
        DocumentStatus.RETRY_PENDING.value,
    })

    def can_retry(self, status: str) -> bool:
        return status in self._RETRYABLE_STATUSES

    def schedule_retry(
        self,
        repository: DocumentRepository,
        document_id: uuid.UUID,
        *,
        user_id: str,
        event_collector: LifecycleEventCollector,
    ) -> DocumentRetryResult:
        document = repository.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")
        if not self.can_retry(document.status):
            raise DocumentIngestionError(
                f"Document '{document_id}' is not eligible for retry."
            )

        repository.update_status(document_id, DocumentStatus.RETRY_PENDING)
        event_collector.publish(
            DocumentRetryScheduled(
                document_id=str(document_id),
                user_id=user_id,
                checksum=document.checksum,
            )
        )
        return DocumentRetryResult.scheduled(str(document_id))

    def mark_retry_completed(
        self,
        repository: DocumentRepository,
        document_id: uuid.UUID,
        *,
        user_id: str,
        final_status: DocumentStatus,
        event_collector: LifecycleEventCollector,
    ) -> DocumentRetryResult:
        """Record successful retry completion. Called after pipeline re-run."""
        updated = repository.update_status(document_id, final_status)
        if updated is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found.")
        event_collector.publish(
            DocumentRetryCompleted(
                document_id=str(document_id),
                user_id=user_id,
                checksum=updated.checksum,
            )
        )
        return DocumentRetryResult.completed(
            str(document_id),
            final_status=final_status,
        )
