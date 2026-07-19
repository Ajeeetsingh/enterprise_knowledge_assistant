"""FastAPI dependency injection."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db as _get_db
from app.db.repositories.document_repository import DocumentRepository
from app.services.audit_dependencies import (
    get_audit_repository,
    get_audit_service,
    parse_audit_search_request,
)
from app.services.monitoring_dependencies import get_metrics_service, get_monitoring_service
from app.services.conversation_chat_service import (
    ConversationChatService,
    build_conversation_chat_service,
)
from app.services.conversation_service import (
    ConversationService,
    build_conversation_service,
)
from app.services.document_service import DocumentService, get_document_service as _get_document_service
from app.services.rag_service import RagService, get_rag_service as _get_rag_service
from app.services.suggested_questions import (
    SuggestedQuestionService,
    get_suggested_question_service as _get_suggested_question_service,
)

# Re-export database session dependency
get_db = _get_db


def get_rag_service_dep() -> RagService:
    """Return the cached RAG service for route injection."""
    return _get_rag_service()


def get_document_service_dep() -> DocumentService:
    """Return the cached document service for route injection."""
    return _get_document_service()


def get_suggested_question_service_dep() -> SuggestedQuestionService:
    """Return the cached suggested-question service for route injection."""
    return _get_suggested_question_service()


def get_document_repository(db: Session = Depends(get_db)) -> DocumentRepository:
    """Return a document repository bound to the current database session."""
    return DocumentRepository(db)


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """Return a conversation service bound to the current database session."""
    return build_conversation_service(db)


def get_conversation_chat_service(
    db: Session = Depends(get_db),
) -> ConversationChatService:
    """Return a conversation chat service bound to the current database session."""
    return build_conversation_chat_service(db)


__all__ = [
    "get_audit_repository",
    "get_audit_service",
    "get_conversation_chat_service",
    "get_conversation_service",
    "get_db",
    "get_document_repository",
    "get_document_service_dep",
    "get_metrics_service",
    "get_monitoring_service",
    "get_rag_service_dep",
    "get_suggested_question_service_dep",
    "parse_audit_search_request",
]
