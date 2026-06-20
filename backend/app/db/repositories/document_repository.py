"""Document metadata repository — PostgreSQL only, no file or pipeline logic."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.documents.status import DocumentStatus


@dataclass(frozen=True)
class DocumentFilter:
    """Optional metadata filters for document listing."""

    filename: str | None = None
    status: DocumentStatus | None = None
    uploaded_by: uuid.UUID | None = None


class DocumentRepository:
    """CRUD and query operations for document metadata."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        document_id: uuid.UUID,
        filename: str,
        content_type: str,
        file_size: int,
        checksum: str,
        storage_path: str,
        uploaded_by: uuid.UUID,
        status: DocumentStatus,
        tenant_id: str | None = None,
        version: int = 1,
        parent_document_id: uuid.UUID | None = None,
    ) -> Document:
        """Persist a new document metadata record."""
        document = Document(
            id=document_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            checksum=checksum,
            storage_path=storage_path,
            uploaded_by=uploaded_by,
            status=status.value,
            tenant_id=tenant_id,
            version=version,
            parent_document_id=parent_document_id,
        )
        self._db.add(document)
        self._db.commit()
        self._db.refresh(document)
        return document

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        """Return a document by primary key, or ``None`` if not found."""
        return self._db.get(Document, document_id)

    def exists(self, document_id: uuid.UUID) -> bool:
        """Return whether a document with the given ID exists."""
        return (
            self._db.scalar(
                select(Document.id).where(Document.id == document_id)
            )
            is not None
        )

    def list(
        self,
        *,
        limit: int,
        offset: int,
        filters: DocumentFilter | None = None,
    ) -> tuple[list[Document], int]:
        """Return a page of documents and the total matching count."""
        query = select(Document)
        count_query = select(func.count()).select_from(Document)

        if filters is not None:
            if filters.filename:
                pattern = f"%{filters.filename}%"
                query = query.where(Document.filename.ilike(pattern))
                count_query = count_query.where(Document.filename.ilike(pattern))
            if filters.status is not None:
                query = query.where(Document.status == filters.status.value)
                count_query = count_query.where(
                    Document.status == filters.status.value
                )
            if filters.uploaded_by is not None:
                query = query.where(Document.uploaded_by == filters.uploaded_by)
                count_query = count_query.where(
                    Document.uploaded_by == filters.uploaded_by
                )

        total = self._db.scalar(count_query) or 0
        documents = list(
            self._db.scalars(
                query.order_by(Document.uploaded_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return documents, total

    def update(self, document: Document) -> Document:
        """Persist changes to an existing document record."""
        self._db.add(document)
        self._db.commit()
        self._db.refresh(document)
        return document

    def update_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
    ) -> Document | None:
        """Update only the lifecycle status of a document."""
        document = self.get_by_id(document_id)
        if document is None:
            return None
        document.status = status.value
        return self.update(document)

    def mark_deleted(self, document_id: uuid.UUID) -> Document | None:
        """Mark a document as deleted without removing the metadata row."""
        return self.update_status(document_id, DocumentStatus.DELETED)

    def find_by_checksum(
        self,
        checksum: str,
        *,
        exclude_deleted: bool = True,
    ) -> list[Document]:
        """Return all documents matching a content checksum."""
        query = select(Document).where(Document.checksum == checksum)
        if exclude_deleted:
            query = query.where(Document.status != DocumentStatus.DELETED.value)
        return list(
            self._db.scalars(query.order_by(Document.uploaded_at.desc()))
        )

    def exists_checksum(
        self,
        checksum: str,
        *,
        exclude_deleted: bool = True,
    ) -> bool:
        """Return whether any non-deleted document has the given checksum."""
        query = select(Document.id).where(Document.checksum == checksum)
        if exclude_deleted:
            query = query.where(Document.status != DocumentStatus.DELETED.value)
        return self._db.scalar(query.limit(1)) is not None

    def find_latest_version(
        self,
        checksum: str,
        *,
        exclude_deleted: bool = True,
    ) -> Document | None:
        """Return the latest version record for a content checksum."""
        query = select(Document).where(Document.checksum == checksum)
        if exclude_deleted:
            query = query.where(Document.status != DocumentStatus.DELETED.value)
        return self._db.scalar(
            query.order_by(Document.version.desc(), Document.uploaded_at.desc()).limit(1)
        )

    def find_by_filename(
        self,
        filename: str,
        *,
        exclude_deleted: bool = True,
    ) -> Document | None:
        """Return the most recent document with an exact filename match."""
        query = select(Document).where(Document.filename == filename)
        if exclude_deleted:
            query = query.where(Document.status != DocumentStatus.DELETED.value)
        return self._db.scalar(query.order_by(Document.uploaded_at.desc()).limit(1))
