"""Unit tests for document lifecycle persisted audit integration (Phase 7.4)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.services import document_audit_integration
from app.services.audit_service import AuditService


@pytest.fixture
def mock_audit_service() -> MagicMock:
    service = MagicMock(spec=AuditService)
    service.log_event = AsyncMock(return_value=None)
    return service


def _sample_document(**overrides: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "filename": "handbook.pdf",
        "content_type": "application/pdf",
        "visibility": "public",
        "version": 2,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestDocumentUploadAudit:
    def test_document_upload_event(self, mock_audit_service: MagicMock) -> None:
        user_id = uuid.uuid4()
        document_id = uuid.uuid4()

        document_audit_integration.record_document_uploaded(
            mock_audit_service,
            user_id=user_id,
            document_id=document_id,
            document_name="handbook.pdf",
            document_type="application/pdf",
            visibility="public",
            version=1,
            ip_address="192.0.2.1",
            user_agent="pytest/1.0",
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "document.uploaded"
        assert kwargs["event_category"] is AuditEventCategory.DOCUMENT
        assert kwargs["action"] == "upload"
        assert kwargs["status"] is AuditStatus.SUCCESS
        assert kwargs["user_id"] == user_id
        assert kwargs["resource_type"] == "document"
        assert kwargs["resource_id"] == str(document_id)
        assert kwargs["metadata"] == {
            "document_name": "handbook.pdf",
            "document_type": "application/pdf",
            "visibility": "public",
            "version": "1",
        }


class TestDocumentDeleteAudit:
    def test_document_delete_event(self, mock_audit_service: MagicMock) -> None:
        user_id = uuid.uuid4()
        document_id = uuid.uuid4()

        document_audit_integration.record_document_deleted(
            mock_audit_service,
            user_id=user_id,
            document_id=document_id,
            document_name="policy.docx",
            document_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            visibility="restricted",
            version=3,
        )

        mock_audit_service.log_event.assert_awaited_once()
        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["event_type"] == "document.deleted"
        assert kwargs["event_category"] is AuditEventCategory.DOCUMENT
        assert kwargs["action"] == "delete"
        assert kwargs["status"] is AuditStatus.SUCCESS
        assert kwargs["resource_id"] == str(document_id)


class TestDocumentAuditMetadata:
    def test_metadata_from_document(self) -> None:
        document = _sample_document()

        metadata = document_audit_integration.metadata_from_document(document)  # type: ignore[arg-type]

        assert metadata == {
            "document_name": "handbook.pdf",
            "document_type": "application/pdf",
            "visibility": "public",
            "version": "2",
        }

    def test_record_from_document_helper_populates_metadata(
        self,
        mock_audit_service: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        document = _sample_document()

        document_audit_integration.record_document_uploaded_from_document(
            mock_audit_service,
            user_id=user_id,
            document=document,  # type: ignore[arg-type]
        )

        kwargs = mock_audit_service.log_event.await_args.kwargs
        assert kwargs["metadata"]["document_name"] == "handbook.pdf"
        assert kwargs["metadata"]["document_type"] == "application/pdf"
        assert kwargs["metadata"]["visibility"] == "public"
        assert kwargs["metadata"]["version"] == "2"


class TestSkippedDocumentAuditEvents:
    def test_replace_event_not_integrated(self) -> None:
        """``document.replaced`` is skipped — replacement is not implemented."""

        assert not hasattr(document_audit_integration, "record_document_replaced")

    def test_reindex_event_not_integrated(self) -> None:
        """``document.reindexed`` is skipped — no user-facing reindex workflow."""

        assert not hasattr(document_audit_integration, "record_document_reindexed")


class TestDocumentAuditFailureDoesNotBreakWorkflow:
    def test_repository_failure_does_not_raise_from_upload_helper(self) -> None:
        repository = MagicMock()
        repository.create.side_effect = RuntimeError("database down")
        service = AuditService(repository)

        document_audit_integration.record_document_uploaded(
            service,
            user_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            document_name="notes.txt",
            document_type="text/plain",
        )

    @patch("app.services.document_audit_integration.run_persisted_audit", return_value=None)
    def test_record_helpers_do_not_raise_when_persisted_audit_returns_none(
        self,
        _mock_run_persisted: MagicMock,
        mock_audit_service: MagicMock,
    ) -> None:
        user_id = uuid.uuid4()
        document = _sample_document()

        document_audit_integration.record_document_uploaded_from_document(
            mock_audit_service,
            user_id=user_id,
            document=document,  # type: ignore[arg-type]
        )
        document_audit_integration.record_document_deleted_from_document(
            mock_audit_service,
            user_id=user_id,
            document=document,  # type: ignore[arg-type]
        )
