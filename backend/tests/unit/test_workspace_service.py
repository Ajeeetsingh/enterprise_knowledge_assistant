"""Unit tests for workspace summary aggregation."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.schemas.workspace import WorkspaceSummaryResponse
from app.services.workspace_service import WorkspaceService


def test_workspace_summary_uses_authorized_document_total() -> None:
    user = MagicMock()
    user.id = uuid.uuid4()

    document_service = MagicMock()
    document_service.list_documents.return_value = ([], 7)

    conversation_repository = MagicMock()
    conversation_repository.list_by_user.return_value = ([], 3)

    message_repository = MagicMock()
    message_repository.count_user_questions.return_value = 11

    service = WorkspaceService(
        document_service=document_service,
        document_repository=MagicMock(),
        conversation_repository=conversation_repository,
        message_repository=message_repository,
    )

    summary = service.get_summary(user)

    assert summary == WorkspaceSummaryResponse(
        documents_available=7,
        conversations=3,
        questions_asked=11,
        collections=None,
    )
    document_service.list_documents.assert_called_once()
    assert document_service.list_documents.call_args.kwargs["viewer"] is user
