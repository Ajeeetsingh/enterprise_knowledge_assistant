"""Rebuild the in-process vector index from searchable documents on startup."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_with_fields
from app.db.repositories.document_repository import DocumentFilter, DocumentRepository
from app.documents.status import DocumentStatus
from app.documents.types import IngestionContext
from app.services.document_service import DocumentService

logger = get_logger(__name__)


def bootstrap_search_index(
    session: Session,
    document_service: DocumentService,
    *,
    limit: int = 10_000,
) -> int:
    """Populate the shared vector store from persisted searchable documents.

    Called during application startup when the in-memory FAISS index is empty
    (e.g. after a process restart). Documents indexed during the current process
    lifetime are left untouched.
    """
    store = document_service.vector_store
    if store.size > 0:
        log_with_fields(
            logger,
            logging.INFO,
            "Vector index bootstrap skipped",
            reason="index_already_populated",
            vector_count=store.size,
        )
        return store.size

    repository = DocumentRepository(session)
    documents, total = repository.list(
        limit=limit,
        offset=0,
        filters=DocumentFilter(status=DocumentStatus.SEARCHABLE),
    )

    if not documents:
        log_with_fields(
            logger,
            logging.INFO,
            "Vector index bootstrap skipped",
            reason="no_searchable_documents",
        )
        return 0

    indexed = 0
    for document in documents:
        storage_path = document.storage_path
        if not storage_path or storage_path.startswith("pending/"):
            log_with_fields(
                logger,
                logging.WARNING,
                "Skipping bootstrap for document without stored content",
                document_id=str(document.id),
                filename=document.filename,
            )
            continue
        try:
            content = document_service.storage.resolve(storage_path).read_bytes()
            document_service.reindex_document_vectors(
                document_id=str(document.id),
                filename=document.filename,
                content_type=document.content_type,
                content=content,
            )
            indexed += 1
        except Exception as exc:
            log_with_fields(
                logger,
                logging.ERROR,
                "Failed to bootstrap document into vector index",
                document_id=str(document.id),
                filename=document.filename,
                reason=type(exc).__name__,
            )

    log_with_fields(
        logger,
        logging.INFO,
        "Vector index bootstrap completed",
        searchable_documents=total,
        documents_indexed=indexed,
        vector_count=store.size,
    )
    return store.size
