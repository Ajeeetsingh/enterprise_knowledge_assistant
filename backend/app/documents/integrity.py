"""Document integrity policy and content-identity decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol

from app.db.repositories.document_repository import DocumentRepository

if TYPE_CHECKING:
    from app.db.models.document import Document


class _ExistingDocumentLike(Protocol):
    id: object
    filename: str
    checksum: str


class IntegrityDecision(StrEnum):
    """Outcome of a pre-upload integrity evaluation."""

    NEW_DOCUMENT = "new_document"
    EXACT_DUPLICATE = "exact_duplicate"
    CONTENT_CHANGED = "content_changed"
    FILENAME_CONFLICT = "filename_conflict"


@dataclass(frozen=True)
class DocumentIntegrityResult:
    """Business result from an integrity policy evaluation.

    Independent of repository internals and suitable for API mapping.
    """

    decision: IntegrityDecision
    checksum: str
    filename: str
    message: str
    document_id: str | None = None
    existing_filename: str | None = None

    @classmethod
    def for_new_document(cls, *, checksum: str, filename: str) -> DocumentIntegrityResult:
        return cls(
            decision=IntegrityDecision.NEW_DOCUMENT,
            checksum=checksum,
            filename=filename,
            message="No existing document matches this content identity.",
        )

    @classmethod
    def for_exact_duplicate(
        cls,
        *,
        checksum: str,
        filename: str,
        existing: _ExistingDocumentLike,
    ) -> DocumentIntegrityResult:
        return cls(
            decision=IntegrityDecision.EXACT_DUPLICATE,
            checksum=checksum,
            filename=filename,
            document_id=str(existing.id),
            existing_filename=existing.filename,
            message=(
                f"{filename} has already been uploaded."
                if filename
                else "This document has already been uploaded."
            ),
        )

    @classmethod
    def for_filename_conflict(
        cls,
        *,
        checksum: str,
        filename: str,
        existing: _ExistingDocumentLike,
    ) -> DocumentIntegrityResult:
        return cls(
            decision=IntegrityDecision.FILENAME_CONFLICT,
            checksum=checksum,
            filename=filename,
            document_id=str(existing.id),
            existing_filename=existing.filename,
            message=(
                f"Filename '{filename}' is already used by another document "
                f"with different content."
            ),
        )

    @classmethod
    def for_content_changed(
        cls,
        *,
        checksum: str,
        filename: str,
        existing: _ExistingDocumentLike,
    ) -> DocumentIntegrityResult:
        return cls(
            decision=IntegrityDecision.CONTENT_CHANGED,
            checksum=checksum,
            filename=filename,
            document_id=str(existing.id),
            existing_filename=existing.filename,
            message=(
                f"Content for '{filename}' differs from the existing document. "
                "Replacement is not yet supported."
            ),
        )


class DuplicateDetectionPolicy:
    """Determine upload integrity outcomes from content and filename identity.

    Business rules live here — not in the API layer or repository.
    Duplicate checks are scoped by tenant so organizations remain isolated.
    Soft-deleted documents are ignored (repository default), allowing re-upload
    after deletion per lifecycle rules.
    """

    def evaluate(
        self,
        repository: DocumentRepository,
        *,
        checksum: str,
        filename: str,
        tenant_id: str | None = None,
    ) -> DocumentIntegrityResult:
        """Evaluate whether an upload should proceed, short-circuit, or reject."""
        normalized_filename = filename.strip()
        existing_by_checksum = repository.find_latest_version(
            checksum,
            tenant_id=tenant_id,
        )
        existing_by_filename = repository.find_by_filename(
            normalized_filename,
            tenant_id=tenant_id,
        )

        if existing_by_checksum is not None:
            return DocumentIntegrityResult.for_exact_duplicate(
                checksum=checksum,
                filename=normalized_filename,
                existing=existing_by_checksum,
            )

        if existing_by_filename is not None:
            if existing_by_filename.checksum != checksum:
                return DocumentIntegrityResult.for_filename_conflict(
                    checksum=checksum,
                    filename=normalized_filename,
                    existing=existing_by_filename,
                )

        return DocumentIntegrityResult.for_new_document(
            checksum=checksum,
            filename=normalized_filename,
        )
