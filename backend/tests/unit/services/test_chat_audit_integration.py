"""Unit tests for chat persisted audit integration (Phase 7.5)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.services import chat_audit_integration
from app.services.audit_service import AuditService


def _mock_audit_service() -> MagicMock:
    service = MagicMock(spec=AuditService)
    service.log_event = AsyncMock(return_value=None)
    return service


class TestChatQuestionAskedAudit:
    def test_question_asked_event(self) -> None:
        mock_audit_service = _mock_audit_service()
        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        chat_audit_integration.record_question_asked(
            mock_audit_service,
            user_id=user_id,
            conversation_id=conversation_id,
            query_length=42,
            ip_address="192.0.2.1",
            user_agent="pytest/1.0",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "chat.question.asked"
        assert kwargs["event_category"] is AuditEventCategory.CHAT
        assert kwargs["status"] is AuditStatus.SUCCESS
        assert kwargs["user_id"] == user_id
        assert kwargs["resource_type"] == "conversation"
        assert kwargs["resource_id"] == str(conversation_id)
        assert kwargs["metadata"] == {
            "conversation_id": str(conversation_id),
            "query_length": 42,
        }
        assert "question" not in str(kwargs["metadata"]).lower()


class TestChatAnswerGeneratedAudit:
    def test_answer_generated_event(self) -> None:
        mock_audit_service = _mock_audit_service()
        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        chat_audit_integration.record_answer_generated(
            mock_audit_service,
            user_id=user_id,
            conversation_id=conversation_id,
            citation_count=3,
            confidence_score=0.91,
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "chat.answer.generated"
        assert kwargs["event_category"] is AuditEventCategory.CHAT
        assert kwargs["status"] is AuditStatus.SUCCESS
        assert kwargs["metadata"] == {
            "conversation_id": str(conversation_id),
            "citation_count": 3,
            "confidence_score": 0.91,
        }


class TestChatRetrievalFailedAudit:
    def test_retrieval_failed_event(self) -> None:
        mock_audit_service = _mock_audit_service()
        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        chat_audit_integration.record_retrieval_failed(
            mock_audit_service,
            user_id=user_id,
            conversation_id=conversation_id,
            reason="Failed to process knowledge request.",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "chat.retrieval.failed"
        assert kwargs["event_category"] is AuditEventCategory.CHAT
        assert kwargs["status"] is AuditStatus.FAILED
        assert kwargs["metadata"] == {
            "conversation_id": str(conversation_id),
            "reason": "Failed to process knowledge request.",
        }
        assert "traceback" not in kwargs["metadata"]["reason"].lower()


class TestChatAuditFailureNonFatal:
    def test_repository_failure_does_not_raise(self) -> None:
        repository = MagicMock()
        repository.create.side_effect = RuntimeError("database down")
        service = AuditService(repository)

        chat_audit_integration.record_question_asked(
            service,
            user_id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            query_length=10,
        )

    @patch("app.services.chat_audit_integration.run_persisted_audit", return_value=None)
    def test_record_helpers_do_not_raise_when_persisted_audit_returns_none(
        self,
        _mock_run_persisted: MagicMock,
    ) -> None:
        mock_audit_service = _mock_audit_service()
        user_id = uuid.uuid4()
        conversation_id = uuid.uuid4()

        chat_audit_integration.record_question_asked(
            mock_audit_service,
            user_id=user_id,
            conversation_id=conversation_id,
            query_length=5,
        )
        chat_audit_integration.record_answer_generated(
            mock_audit_service,
            user_id=user_id,
            conversation_id=conversation_id,
            citation_count=0,
        )
        chat_audit_integration.record_retrieval_failed(
            mock_audit_service,
            user_id=user_id,
            conversation_id=conversation_id,
            reason="Failed to process knowledge request.",
        )
