"""Document replacement foundation — implementation reserved for a future phase."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.db.repositories.document_repository import DocumentRepository
from app.documents.status import DocumentUploadResult


class DocumentReplacementHandler(ABC):
    """Contract for future document replacement operations.

    ``DocumentService.replace_document()`` will delegate to an implementation
    of this handler without changing the public upload API.
    """

    @abstractmethod
    def replace_document(
        self,
        repository: DocumentRepository,
        *,
        document_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
        replaced_by: uuid.UUID,
    ) -> DocumentUploadResult:
        """Replace an existing document while preserving version lineage."""


class UnimplementedReplacementHandler(DocumentReplacementHandler):
    """Placeholder until replacement is implemented in a future phase."""

    def replace_document(
        self,
        repository: DocumentRepository,
        *,
        document_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
        replaced_by: uuid.UUID,
    ) -> DocumentUploadResult:
        raise NotImplementedError("Document replacement is not yet implemented.")
