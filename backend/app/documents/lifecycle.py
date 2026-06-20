"""Document lifecycle business result types."""

from __future__ import annotations

from dataclasses import dataclass

from app.documents.status import DocumentStatus


@dataclass(frozen=True)
class DocumentLifecycleResult:
    """Business result returned by lifecycle operations such as delete.

    Hides storage, vector store, and repository internals from the API layer.
    """

    document_id: str
    status: DocumentStatus
    message: str

    @classmethod
    def deleted(cls, document_id: str, *, already_deleted: bool = False) -> DocumentLifecycleResult:
        """Build a result for a successful delete (or idempotent re-delete)."""
        if already_deleted:
            message = f"Document '{document_id}' was already deleted."
        else:
            message = f"Document '{document_id}' deleted successfully."
        return cls(
            document_id=document_id,
            status=DocumentStatus.DELETED,
            message=message,
        )
