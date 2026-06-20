"""Unit tests for document upload response mapping."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.documents.metadata import DocumentMetadata, IndexingStatus
from app.documents.status import DocumentStatus, DocumentUploadResult
from app.documents.types import IngestionResult
from app.mappers.documents import (
    map_to_detail_response,
    map_to_lifecycle_response,
    map_to_paginated_response,
    map_to_summary_response,
    map_to_upload_response,
)


def _ingestion_result(*, indexed: bool = True) -> IngestionResult:
    metadata = DocumentMetadata(
        filename="policy.txt",
        content_type="text/plain",
        checksum="abc123",
        uploaded_at=datetime.now(UTC),
        indexing_status=IndexingStatus.INDEXED if indexed else IndexingStatus.PENDING,
        document_id="doc-123",
        storage_path="/internal/path/policy.txt",
    )
    return IngestionResult(
        metadata=metadata,
        storage_path="/internal/path/policy.txt",
        chunk_count=2 if indexed else 0,
        embedding_count=2 if indexed else 0,
        indexed=indexed,
    )


def test_map_to_upload_response_searchable() -> None:
    result = DocumentUploadResult.from_ingestion(_ingestion_result(indexed=True))

    response = map_to_upload_response(result)

    assert response.document_id == "doc-123"
    assert response.filename == "policy.txt"
    assert response.status == DocumentStatus.SEARCHABLE
    assert "searchable" in response.message.lower()


def test_map_to_upload_response_stored_when_not_indexed() -> None:
    result = DocumentUploadResult.from_ingestion(_ingestion_result(indexed=False))

    response = map_to_upload_response(result)

    assert response.status == DocumentStatus.STORED


def test_response_excludes_internal_fields() -> None:
    result = DocumentUploadResult.from_ingestion(_ingestion_result())

    response = map_to_upload_response(result)
    payload = response.model_dump()

    assert "storage_path" not in payload
    assert "chunk_count" not in payload
    assert "checksum" not in payload


def _document_entity(**overrides) -> SimpleNamespace:
    document_id = overrides.pop("document_id", uuid4())
    defaults = {
        "id": document_id,
        "filename": "policy.txt",
        "content_type": "text/plain",
        "file_size": 42,
        "checksum": "abc123",
        "status": DocumentStatus.SEARCHABLE.value,
        "uploaded_at": datetime.now(UTC),
        "uploaded_by": uuid4(),
        "storage_path": "/internal/path/policy.txt",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_map_to_summary_response() -> None:
    document = _document_entity()

    response = map_to_summary_response(document)

    assert response.document_id == str(document.id)
    assert response.filename == "policy.txt"
    assert response.status == DocumentStatus.SEARCHABLE
    assert "storage_path" not in response.model_dump()


def test_map_to_detail_response_excludes_storage_path() -> None:
    document = _document_entity()

    response = map_to_detail_response(document)
    payload = response.model_dump()

    assert payload["checksum"] == "abc123"
    assert payload["file_size"] == 42
    assert "storage_path" not in payload


def test_map_to_paginated_response() -> None:
    documents = [_document_entity(filename="a.txt"), _document_entity(filename="b.txt")]

    response = map_to_paginated_response(
        documents,
        total=5,
        limit=2,
        offset=0,
    )

    assert response.total == 5
    assert response.limit == 2
    assert response.offset == 0
    assert len(response.items) == 2


def test_map_to_lifecycle_response() -> None:
    from app.documents.lifecycle import DocumentLifecycleResult

    result = DocumentLifecycleResult.deleted("doc-123")
    response = map_to_lifecycle_response(result)

    assert response.document_id == "doc-123"
    assert response.status == DocumentStatus.DELETED
    assert "deleted" in response.message.lower()
