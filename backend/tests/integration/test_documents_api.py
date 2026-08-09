"""Integration tests for document management API."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.exceptions import DocumentValidationError
from app.db.models import Document, User
from app.db.repositories.document_repository import DocumentRepository
from app.dependencies import get_db, get_document_service_dep
from app.documents.status import DocumentStatus, DocumentUploadResult
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.vector_store.base import VectorStore
from app.main import app
from app.services.document_service import build_document_service
from app.storage.local import LocalStorage
from app.auth.dependencies import AUTHORIZATION_DENIED_MESSAGE
from tests.helpers.knowledge_domains import make_knowledge_domain
from tests.integration.conftest import access_token_for, bearer_headers

UPLOAD_URL = "/api/v1/documents/upload"
LIST_URL = "/api/v1/documents"

PUBLIC_RESPONSE_FIELDS = {
    "document_id",
    "filename",
    "status",
    "message",
}

INTERNAL_RESPONSE_FIELDS = {
    "storage_path",
    "chunk_count",
    "embedding_count",
    "indexed",
    "checksum",
    "metadata",
    "chunks",
    "embeddings",
    "vector_ids",
}


def _fake_upload_result(
    *,
    document_id: str = "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    filename: str = "policy.txt",
    status: DocumentStatus = DocumentStatus.SEARCHABLE,
) -> DocumentUploadResult:
    return DocumentUploadResult(
        document_id=document_id,
        filename=filename,
        status=status,
        message=f"Document '{filename}' uploaded and is now searchable.",
    )


@pytest.fixture
def mock_document_service() -> MagicMock:
    service = MagicMock()
    service.upload_document.return_value = _fake_upload_result()
    return service


@pytest.fixture
def documents_client(
    db_session: Session,
    mock_document_service: MagicMock,
) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_document_service_dep] = lambda: mock_document_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _upload_file(
    client: TestClient,
    token: str,
    *,
    filename: str = "policy.txt",
    content: bytes = b"Annual leave: 20 days per year.",
    content_type: str = "text/plain",
    domain_id: str | None = None,
) -> TestClient:
    resolved_domain_id = domain_id or getattr(
        client, "upload_domain_id", None
    ) or str(uuid.uuid4())
    return client.post(
        UPLOAD_URL,
        headers=bearer_headers(token),
        files={"file": (filename, content, content_type)},
        data={"domain_id": resolved_domain_id},
    )


def test_admin_upload_returns_document_upload_response(
    documents_client: TestClient,
    mock_document_service: MagicMock,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)

    response = _upload_file(documents_client, token)

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == PUBLIC_RESPONSE_FIELDS
    assert INTERNAL_RESPONSE_FIELDS.isdisjoint(data.keys())
    assert data["document_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert data["filename"] == "policy.txt"
    assert data["status"] == "searchable"
    assert "searchable" in data["message"].lower()
    mock_document_service.upload_document.assert_called_once()
    call_kwargs = mock_document_service.upload_document.call_args.kwargs
    assert call_kwargs["filename"] == "policy.txt"
    assert call_kwargs["content"] == b"Annual leave: 20 days per year."
    assert "domain_id" in call_kwargs
    assert call_kwargs["domain_repository"] is not None


def test_document_id_is_returned(
    documents_client: TestClient,
    mock_document_service: MagicMock,
    admin_user: User,
) -> None:
    document_id = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    mock_document_service.upload_document.return_value = _fake_upload_result(
        document_id=document_id,
    )
    token = access_token_for(admin_user)

    response = _upload_file(documents_client, token)

    assert response.status_code == 200
    assert response.json()["document_id"] == document_id


def test_lifecycle_status_returned(
    documents_client: TestClient,
    mock_document_service: MagicMock,
    admin_user: User,
) -> None:
    mock_document_service.upload_document.return_value = _fake_upload_result(
        status=DocumentStatus.STORED,
    )
    token = access_token_for(admin_user)

    response = _upload_file(documents_client, token)

    assert response.status_code == 200
    assert response.json()["status"] == "stored"


def test_unsupported_file_type_returns_422(
    documents_client: TestClient,
    mock_document_service: MagicMock,
    admin_user: User,
) -> None:
    mock_document_service.upload_document.side_effect = DocumentValidationError(
        "Unsupported file extension '.exe'."
    )
    token = access_token_for(admin_user)

    response = _upload_file(
        documents_client,
        token,
        filename="malware.exe",
        content=b"bad",
        content_type="application/octet-stream",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Document validation failed."


def test_invalid_empty_upload_returns_422(
    documents_client: TestClient,
    mock_document_service: MagicMock,
    admin_user: User,
) -> None:
    mock_document_service.upload_document.side_effect = DocumentValidationError(
        "Document content must not be empty."
    )
    token = access_token_for(admin_user)

    response = _upload_file(documents_client, token, content=b"")

    assert response.status_code == 422
    assert response.json()["detail"] == "Document validation failed."


def test_missing_jwt_returns_401(documents_client: TestClient) -> None:
    response = documents_client.post(
        UPLOAD_URL,
        files={"file": ("policy.txt", b"content", "text/plain")},
        data={"domain_id": str(uuid.uuid4())},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_invalid_jwt_returns_401(documents_client: TestClient) -> None:
    response = documents_client.post(
        UPLOAD_URL,
        headers=bearer_headers("invalid-token"),
        files={"file": ("policy.txt", b"content", "text/plain")},
        data={"domain_id": str(uuid.uuid4())},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials."


def test_non_admin_user_returns_403(
    documents_client: TestClient,
    mock_document_service: MagicMock,
    active_user: User,
) -> None:
    token = access_token_for(active_user)

    response = _upload_file(documents_client, token)

    assert response.status_code == 403
    assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE
    mock_document_service.upload_document.assert_not_called()


def test_hr_user_can_upload(
    documents_client: TestClient,
    mock_document_service: MagicMock,
    hr_user: User,
) -> None:
    token = access_token_for(hr_user)

    response = _upload_file(documents_client, token)

    assert response.status_code == 200
    mock_document_service.upload_document.assert_called_once()


def test_documents_route_has_no_manual_exception_handling() -> None:
    documents_source = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "api"
        / "v1"
        / "documents.py"
    ).read_text(encoding="utf-8")

    assert "DocumentValidationError" not in documents_source
    assert "DocumentIngestionError" not in documents_source
    assert "except " not in documents_source
    assert "pipeline" not in documents_source.lower()
    assert "ingest(" not in documents_source


def test_openapi_includes_document_models(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]

    assert "DocumentUploadResponse" in schemas
    assert "ErrorResponse" in schemas
    assert "DocumentStatus" in schemas

    upload_op = response.json()["paths"]["/api/v1/documents/upload"]["post"]
    assert upload_op["summary"] == "Upload an enterprise document"
    assert "200" in upload_op["responses"]
    assert "401" in upload_op["responses"]
    assert "403" in upload_op["responses"]
    assert "422" in upload_op["responses"]
    assert "500" in upload_op["responses"]
    assert upload_op["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("DocumentUploadResponse")


def _mock_processor(text: str = "policy text") -> MagicMock:
    proc = MagicMock(spec=DocumentProcessor)
    proc.process.return_value = text
    return proc


def _mock_embedder() -> MagicMock:
    emb = MagicMock(spec=EmbeddingProvider)
    emb.embed.side_effect = lambda texts: [[0.1] * 4 for _ in texts]
    return emb


def _mock_store() -> MagicMock:
    store = MagicMock(spec=VectorStore)
    store.add_chunks.side_effect = (
        lambda chunks, embs, document_id=None: [c.chunk_id for c in chunks]
    )
    return store


@pytest.fixture
def real_document_client(
    db_session: Session,
    tmp_path: Path,
) -> TestClient:
    storage = LocalStorage(base_path=tmp_path)
    service = build_document_service(
        storage=storage,
        processor=_mock_processor("Annual leave policy."),
        embedding_provider=_mock_embedder(),
        vector_store=_mock_store(),
    )
    domain = make_knowledge_domain(db_session, name="Finance")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_document_service_dep] = lambda: service
    with TestClient(app) as test_client:
        test_client.upload_domain_id = str(domain.id)  # type: ignore[attr-defined]
        yield test_client
    app.dependency_overrides.clear()


def test_upload_persists_metadata_in_database(
    real_document_client: TestClient,
    db_session: Session,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)

    response = _upload_file(real_document_client, token, filename="policy.txt")

    assert response.status_code == 200
    document_id = response.json()["document_id"]
    repository = DocumentRepository(db_session)
    persisted = repository.get_by_id(uuid.UUID(document_id))

    assert persisted is not None
    assert persisted.filename == "policy.txt"
    assert persisted.uploaded_by == admin_user.id
    assert persisted.status == DocumentStatus.SEARCHABLE.value
    assert persisted.storage_path
    assert persisted.domain_id is not None
    assert str(persisted.domain_id) == real_document_client.upload_domain_id  # type: ignore[attr-defined]


def test_get_document_file_returns_stored_bytes(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    upload_response = _upload_file(real_document_client, token, filename="policy.txt")
    document_id = upload_response.json()["document_id"]

    response = real_document_client.get(
        f"/api/v1/documents/{document_id}/file",
        headers=bearer_headers(token),
    )

    assert response.status_code == 200
    assert response.content
    assert "inline" in response.headers.get("content-disposition", "")


def test_list_documents_returns_paginated_metadata(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    _upload_file(real_document_client, token, filename="alpha.txt", content=b"alpha")
    _upload_file(real_document_client, token, filename="beta.txt", content=b"beta")

    response = real_document_client.get(
        LIST_URL,
        headers=bearer_headers(token),
        params={"limit": 1, "offset": 0},
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"items", "total", "limit", "offset"}
    assert data["total"] == 2
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert len(data["items"]) == 1
    assert set(data["items"][0].keys()) == {
        "document_id",
        "filename",
        "status",
        "uploaded_at",
        "uploaded_by",
        "domain_id",
        "domain_name",
    }
    assert data["items"][0]["domain_id"] is not None
    assert data["items"][0]["domain_name"] is not None
    assert "storage_path" not in data["items"][0]


def test_list_documents_supports_filename_filter(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    _upload_file(
        real_document_client,
        token,
        filename="handbook.pdf",
        content=b"handbook",
        content_type="application/pdf",
    )
    _upload_file(real_document_client, token, filename="notes.txt", content=b"notes")

    response = real_document_client.get(
        LIST_URL,
        headers=bearer_headers(token),
        params={"filename": "hand"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["filename"] == "handbook.pdf"


def test_get_document_returns_detail_metadata(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    upload_response = _upload_file(real_document_client, token)
    document_id = upload_response.json()["document_id"]

    response = real_document_client.get(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == document_id
    assert data["filename"] == "policy.txt"
    assert data["status"] == "searchable"
    assert data["uploaded_by"] == str(admin_user.id)
    assert "checksum" in data
    assert "file_size" in data
    assert "storage_path" not in data


def test_get_document_not_found_returns_404(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)

    response = real_document_client.get(
        f"{LIST_URL}/{uuid.uuid4()}",
        headers=bearer_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_list_documents_allowed_with_document_read_permission(
    real_document_client: TestClient,
    active_user: User,
) -> None:
    token = access_token_for(active_user)

    response = real_document_client.get(LIST_URL, headers=bearer_headers(token))

    assert response.status_code == 200
    assert "items" in response.json()


def test_openapi_includes_list_and_detail_endpoints(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    schemas = response.json()["components"]["schemas"]

    assert "DocumentSummaryResponse" in schemas
    assert "DocumentDetailResponse" in schemas
    assert "PaginatedDocumentResponse" in schemas
    assert paths["/api/v1/documents"]["get"]["summary"] == "List document metadata"
    assert (
        paths["/api/v1/documents/{document_id}"]["get"]["summary"]
        == "Get document metadata"
    )


def test_delete_document_returns_lifecycle_response(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    upload_response = _upload_file(real_document_client, token)
    document_id = upload_response.json()["document_id"]

    response = real_document_client.delete(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"document_id", "status", "message"}
    assert data["document_id"] == document_id
    assert data["status"] == "deleted"
    assert "deleted" in data["message"].lower()


def test_delete_document_updates_metadata_status(
    real_document_client: TestClient,
    db_session: Session,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    upload_response = _upload_file(real_document_client, token)
    document_id = uuid.UUID(upload_response.json()["document_id"])

    real_document_client.delete(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(token),
    )

    repository = DocumentRepository(db_session)
    persisted = repository.get_by_id(document_id)
    assert persisted is not None
    assert persisted.status == "deleted"


def test_list_documents_excludes_deleted_documents(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    upload_response = _upload_file(real_document_client, token, filename="keep.txt")
    document_id = upload_response.json()["document_id"]

    delete_response = real_document_client.delete(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(token),
    )
    assert delete_response.status_code == 200

    list_response = real_document_client.get(
        LIST_URL,
        headers=bearer_headers(token),
    )

    assert list_response.status_code == 200
    data = list_response.json()
    document_ids = {item["document_id"] for item in data["items"]}
    assert document_id not in document_ids


def test_get_deleted_document_returns_404(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    upload_response = _upload_file(real_document_client, token)
    document_id = upload_response.json()["document_id"]

    delete_response = real_document_client.delete(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(token),
    )
    assert delete_response.status_code == 200

    get_response = real_document_client.get(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(token),
    )

    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Document not found."


def test_delete_document_is_idempotent(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    upload_response = _upload_file(real_document_client, token)
    document_id = upload_response.json()["document_id"]

    first = real_document_client.delete(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(token),
    )
    second = real_document_client.delete(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(token),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "deleted"
    assert "already deleted" in second.json()["message"].lower()


def test_delete_document_not_found_returns_404(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)

    response = real_document_client.delete(
        f"{LIST_URL}/{uuid.uuid4()}",
        headers=bearer_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found."


def test_delete_document_requires_admin(
    real_document_client: TestClient,
    active_user: User,
    admin_user: User,
) -> None:
    admin_token = access_token_for(admin_user)
    upload_response = _upload_file(real_document_client, admin_token)
    document_id = upload_response.json()["document_id"]
    employee_token = access_token_for(active_user)

    response = real_document_client.delete(
        f"{LIST_URL}/{document_id}",
        headers=bearer_headers(employee_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


def test_openapi_includes_delete_endpoint(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    delete_op = response.json()["paths"]["/api/v1/documents/{document_id}"]["delete"]

    assert "DocumentLifecycleResponse" in schemas
    assert delete_op["summary"] == "Delete a document"
    assert "200" in delete_op["responses"]
    assert "404" in delete_op["responses"]


def test_duplicate_upload_returns_409_duplicate_document(
    real_document_client: TestClient,
    db_session: Session,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    content = b"Annual leave: 20 days per year."

    first = _upload_file(real_document_client, token, content=content)
    second = _upload_file(
        real_document_client,
        token,
        filename="policy-copy.txt",
        content=content,
    )

    assert first.status_code == 200
    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "DUPLICATE_DOCUMENT"
    assert body["detail"] == "policy-copy.txt has already been uploaded."
    assert "checksum" not in body["detail"].lower()
    assert body["existing_document_id"] == first.json()["document_id"]
    assert "storage_path" not in body

    repository = DocumentRepository(db_session)
    checksum_matches = repository.find_by_checksum(
        repository.get_by_id(uuid.UUID(first.json()["document_id"])).checksum,
        tenant_id="default",
    )
    assert len(checksum_matches) == 1


def test_duplicate_filename_different_content_returns_409(
    real_document_client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    _upload_file(
        real_document_client,
        token,
        filename="policy.txt",
        content=b"original content",
    )

    response = _upload_file(
        real_document_client,
        token,
        filename="policy.txt",
        content=b"different content",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Document integrity check failed."


def test_integrity_response_schema_is_defined() -> None:
    from app.schemas.documents import DocumentIntegrityResponse

    schema = DocumentIntegrityResponse.model_json_schema()
    assert "decision" in schema["properties"]
    assert "checksum" in schema["properties"]
