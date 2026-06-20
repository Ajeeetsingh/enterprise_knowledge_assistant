"""FastAPI dependency injection."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db as _get_db
from app.db.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService, get_document_service as _get_document_service
from app.services.rag_service import RagService, get_rag_service as _get_rag_service

# Re-export database session dependency
get_db = _get_db


def get_rag_service_dep() -> RagService:
    """Return the cached RAG service for route injection."""
    return _get_rag_service()


def get_document_service_dep() -> DocumentService:
    """Return the cached document service for route injection."""
    return _get_document_service()


def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    """Return a document repository bound to the current database session."""
    return DocumentRepository(db)
