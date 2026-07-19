"""Per-user workspace summary for the authenticated dashboard."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.message_repository import MessageRepository
from app.schemas.workspace import WorkspaceSummaryResponse
from app.services.document_service import DocumentService


class WorkspaceService:
    """Aggregate personal workspace counts for the current user."""

    def __init__(
        self,
        *,
        document_service: DocumentService,
        document_repository: DocumentRepository,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
    ) -> None:
        self._document_service = document_service
        self._document_repository = document_repository
        self._conversation_repository = conversation_repository
        self._message_repository = message_repository

    def get_summary(self, user: User) -> WorkspaceSummaryResponse:
        """Return dashboard counts scoped to *user*."""
        _, documents_available = self._document_service.list_documents(
            self._document_repository,
            limit=1,
            offset=0,
            viewer=user,
        )
        _, conversations = self._conversation_repository.list_by_user(
            user.id,
            limit=1,
            offset=0,
        )
        questions_asked = self._message_repository.count_user_questions(user.id)

        return WorkspaceSummaryResponse(
            documents_available=documents_available,
            conversations=conversations,
            questions_asked=questions_asked,
            # Collections are admin UI seed data only — no persisted resource yet.
            collections=None,
        )


def build_workspace_service(
    db: Session,
    document_service: DocumentService,
) -> WorkspaceService:
    """Construct a workspace service bound to *db*."""
    return WorkspaceService(
        document_service=document_service,
        document_repository=DocumentRepository(db),
        conversation_repository=ConversationRepository(db),
        message_repository=MessageRepository(db),
    )
