"""Integration tests for upload-to-retrieval RAG pipeline wiring."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from app.dependencies import get_db, get_document_service_dep, get_rag_service_dep
from app.documents.status import DocumentStatus
from app.ingestion.vector_store.faiss_store import FaissVectorStore
from app.main import app
from app.services.document_service import build_document_service
from app.services.rag_service import RagService
from app.storage.local import LocalStorage
from tests.integration.conftest import access_token_for, admin_user, bearer_headers

UPLOAD_URL = "/api/v1/documents/upload"
SAMPLE_TEXT = (
    "GlobalTrust Financial Services is headquartered in Singapore. "
    "Sarah Mitchell serves as Chief Executive Officer. "
    "The company was founded in 1987."
)


@pytest.fixture
def rag_pipeline_client(
    db_session,
    admin_user,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, FaissVectorStore, RagService]:
    pytest.importorskip("faiss")
    pytest.importorskip("sentence_transformers")

    from app.config import get_settings
    from app.services import document_service as document_service_module

    shared_store = FaissVectorStore()
    storage = LocalStorage(base_path=tmp_path / "storage")
    document_service = build_document_service(
        storage=storage,
        vector_store=shared_store,
    )
    document_service_module.get_document_service.cache_clear()
    monkeypatch.setattr(
        document_service_module,
        "get_document_service",
        lambda: document_service,
    )

    rag_service = RagService(get_settings())

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_document_service_dep] = lambda: document_service
    app.dependency_overrides[get_rag_service_dep] = lambda: rag_service

    with TestClient(app) as test_client:
        yield test_client, shared_store, rag_service

    app.dependency_overrides.clear()


def test_uploaded_document_is_retrievable_via_shared_vector_store(
    rag_pipeline_client: tuple[TestClient, FaissVectorStore, RagService],
    admin_user,
) -> None:
    """Documents indexed during upload must be searchable by the RAG engine."""
    client, shared_store, rag_service = rag_pipeline_client
    token = access_token_for(admin_user)

    response = client.post(
        UPLOAD_URL,
        headers=bearer_headers(token),
        files={
            "file": (
                "GTFS-EXEC-001_Company_Overview.txt",
                SAMPLE_TEXT.encode("utf-8"),
                "text/plain",
            )
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == DocumentStatus.SEARCHABLE.value
    assert shared_store.size > 0

    rag_service.initialize()
    answer = rag_service.answer_question(
        "What is the company headquarters?",
        "Admin",
        authorized_sources=frozenset({"GTFS-EXEC-001_Company_Overview.txt"}),
    )

    assert "No relevant documents found" not in answer.answer
    assert answer.confidence_score > 0
    assert "GTFS-EXEC-001_Company_Overview.txt" in answer.sources_used


def test_index_validation_failure_sets_failed_indexing_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When post-index validation cannot retrieve content, status becomes failed_indexing."""
    pytest.importorskip("faiss")

    shared_store = FaissVectorStore()
    storage = LocalStorage(base_path=tmp_path / "storage")
    document_service = build_document_service(
        storage=storage,
        vector_store=shared_store,
    )
    monkeypatch.setattr(shared_store, "search", lambda *args, **kwargs: [])

    repository = MagicMock()
    document_id = uuid.uuid4()
    repository.find_latest_version.return_value = None
    repository.find_by_filename.return_value = None
    repository.create.return_value = MagicMock(id=document_id)
    repository.get_by_id.return_value = MagicMock(
        id=document_id,
        storage_path="docs/sample.txt",
        status=DocumentStatus.PROCESSING.value,
    )

    with pytest.raises(Exception):
        document_service.upload_document(
            repository,
            filename="sample.txt",
            content_type="text/plain",
            content=SAMPLE_TEXT.encode("utf-8"),
            uploaded_by=uuid.uuid4(),
            domain_id=uuid.uuid4(),
            domain_repository=MagicMock(get_by_id=MagicMock(return_value=MagicMock())),
        )

    repository.update_status.assert_called()
    assert repository.update_status.call_args[0][1] == DocumentStatus.FAILED_INDEXING
