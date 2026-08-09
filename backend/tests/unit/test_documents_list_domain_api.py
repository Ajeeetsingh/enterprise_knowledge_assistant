"""Unit tests for Documents list API domain filter (Phase 3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.documents import list_documents
from app.db.models.knowledge_domain import KnowledgeDomain
from app.documents.status import DocumentStatus


def _admin_user() -> MagicMock:
    user = MagicMock()
    user.is_superuser = True
    user.id = uuid.uuid4()
    return user


def test_list_documents_passes_domain_id_and_filename_to_service() -> None:
    domain_id = uuid.uuid4()
    domain_repository = MagicMock()
    domain_repository.get_by_id.return_value = KnowledgeDomain(
        id=domain_id,
        name="Finance",
        description=None,
    )
    document_service = MagicMock()
    document = SimpleNamespace(
        id=uuid.uuid4(),
        filename="budget.pdf",
        status=DocumentStatus.SEARCHABLE.value,
        uploaded_at=datetime.now(timezone.utc),
        uploaded_by=uuid.uuid4(),
        domain_id=domain_id,
        knowledge_domain=SimpleNamespace(name="Finance"),
    )
    document_service.list_documents.return_value = ([document], 1)
    viewer = _admin_user()

    response = list_documents(
        limit=20,
        offset=0,
        filename="budget",
        status=None,
        uploaded_by=None,
        domain_id=domain_id,
        current_user=viewer,
        document_service=document_service,
        repository=MagicMock(),
        domain_repository=domain_repository,
    )

    kwargs = document_service.list_documents.call_args.kwargs
    assert kwargs["domain_id"] == domain_id
    assert kwargs["filename"] == "budget"
    assert kwargs["viewer"] is viewer
    assert response.total == 1
    assert response.items[0].domain_name == "Finance"
    assert response.items[0].domain_id == domain_id


def test_list_documents_unknown_domain_id_returns_422() -> None:
    domain_repository = MagicMock()
    domain_repository.get_by_id.return_value = None
    document_service = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        list_documents(
            limit=20,
            offset=0,
            filename=None,
            status=None,
            uploaded_by=None,
            domain_id=uuid.uuid4(),
            current_user=_admin_user(),
            document_service=document_service,
            repository=MagicMock(),
            domain_repository=domain_repository,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Knowledge domain not found."
    document_service.list_documents.assert_not_called()


def test_list_documents_without_domain_filter_skips_domain_lookup() -> None:
    domain_repository = MagicMock()
    document_service = MagicMock()
    document_service.list_documents.return_value = ([], 0)

    response = list_documents(
        limit=20,
        offset=0,
        filename=None,
        status=None,
        uploaded_by=None,
        domain_id=None,
        current_user=_admin_user(),
        document_service=document_service,
        repository=MagicMock(),
        domain_repository=domain_repository,
    )

    domain_repository.get_by_id.assert_not_called()
    assert response.total == 0
    assert response.items == []
