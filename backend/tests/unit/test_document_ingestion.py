"""Unit tests for the document ingestion pipeline architecture (Phase 4.1 contract)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from tests.constants import TEST_PASSWORD_HASH
from app.core.exceptions import DocumentIngestionError, DocumentValidationError
from app.db.base import Base
from app.db.models import Document, Role, User  # noqa: F401
from app.db.repositories.document_repository import DocumentRepository
from app.documents.metadata import IndexingStatus
from app.documents.types import IngestionContext
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.pipeline import IngestionPipeline, create_default_pipeline
from app.ingestion.processor import DocumentProcessor
from app.ingestion.stages import (
    ChunkingStage,
    EmbeddingStage,
    ExtractionStage,
    IndexingStage,
    MetadataStage,
    StorageStage,
    ValidationStage,
)
from app.ingestion.stages.base import PipelineStage
from app.ingestion.vector_store.base import VectorStore
from app.services.document_service import DocumentService, get_document_service
from app.storage.interface import StorageAdapter
from app.storage.local import LocalStorage

EXPECTED_STAGE_ORDER = [
    "validation",
    "storage",
    "extraction",
    "chunking",
    "embedding",
    "indexing",
    "metadata",
]


@pytest.fixture(autouse=True)
def clear_document_service_cache() -> None:
    get_document_service.cache_clear()
    yield
    get_document_service.cache_clear()


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


def test_default_pipeline_stage_order(tmp_path: Path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor(),
        embedding_provider=_mock_embedder(),
        vector_store=_mock_store(),
    )
    assert pipeline.stage_names == EXPECTED_STAGE_ORDER


def test_pipeline_construction_requires_stages() -> None:
    with pytest.raises(DocumentIngestionError, match="at least one stage"):
        IngestionPipeline([])


def test_pipeline_run_produces_metadata(tmp_path: Path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor("Annual leave policy content."),
        embedding_provider=_mock_embedder(),
        vector_store=_mock_store(),
    )
    result = pipeline.run(
        IngestionContext(
            filename="hr_policy.txt",
            content_type="text/plain",
            content=b"Annual leave policy content.",
            tenant_id="default",
        )
    )

    assert result.metadata.filename == "hr_policy.txt"
    assert result.metadata.content_type == "text/plain"
    assert result.metadata.checksum
    assert result.storage_path is not None


def test_validation_failure_propagates(tmp_path: Path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor(),
        embedding_provider=_mock_embedder(),
        vector_store=_mock_store(),
    )
    with pytest.raises(DocumentValidationError):
        pipeline.run(
            IngestionContext(
                filename="empty.txt",
                content_type="text/plain",
                content=b"",
            )
        )


def test_pipeline_wraps_unexpected_stage_errors(tmp_path: Path) -> None:
    class FailingStage(PipelineStage):
        @property
        def name(self) -> str:
            return "failing"

        @property
        def description(self) -> str:
            return "Test-only stage that always fails."

        @property
        def order(self) -> int:
            return 99

        def process(self, context: IngestionContext) -> IngestionContext:
            raise RuntimeError("unexpected failure")

    storage = LocalStorage(base_path=tmp_path)
    pipeline = IngestionPipeline([ValidationStage(), FailingStage()])

    with pytest.raises(DocumentIngestionError, match="failing"):
        pipeline.run(
            IngestionContext(
                filename="report.txt",
                content_type="text/plain",
                content=b"content",
            )
        )


def test_local_storage_implements_storage_adapter(tmp_path: Path) -> None:
    storage = LocalStorage(base_path=tmp_path)

    assert isinstance(storage, StorageAdapter)

    saved = storage.save("policies/hr_policy.txt", b"policy content")
    assert saved.exists()
    assert storage.exists("policies/hr_policy.txt")
    assert storage.resolve("policies/hr_policy.txt") == saved

    storage.delete("policies/hr_policy.txt")
    assert not storage.exists("policies/hr_policy.txt")


def test_document_service_uses_pipeline_and_storage(tmp_path: Path) -> None:
    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor("Employee handbook."),
        embedding_provider=_mock_embedder(),
        vector_store=store,
    )
    service = DocumentService(pipeline=pipeline, storage=storage, vector_store=store)

    result = service.ingest(
        filename="handbook.txt",
        content_type="text/plain",
        content=b"Employee handbook.",
    )

    assert result.metadata.filename == "handbook.txt"
    assert service.pipeline.stage_names == EXPECTED_STAGE_ORDER


def test_upload_document_returns_business_result(
    tmp_path: Path,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    role = Role(name="Admin", description="Administrator")
    user = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    session.add_all([role, user])
    session.commit()

    storage = LocalStorage(base_path=tmp_path)
    store = _mock_store()
    pipeline = create_default_pipeline(
        storage,
        processor=_mock_processor("Employee handbook."),
        embedding_provider=_mock_embedder(),
        vector_store=store,
    )
    service = DocumentService(pipeline=pipeline, storage=storage, vector_store=store)
    repository = DocumentRepository(session)

    upload_result = service.upload_document(
        repository,
        filename="handbook.txt",
        content_type="text/plain",
        content=b"Employee handbook.",
        uploaded_by=user.id,
    )

    assert upload_result.document_id
    assert upload_result.filename == "handbook.txt"
    assert upload_result.status.value == "searchable"
    assert "searchable" in upload_result.message.lower()

    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_get_document_service_returns_cached_singleton() -> None:
    first = get_document_service()
    second = get_document_service()

    assert first is second
    assert isinstance(first, DocumentService)
    assert first.pipeline.stage_names == EXPECTED_STAGE_ORDER


def test_ingestion_package_has_no_fastapi_imports() -> None:
    ingestion_root = Path(__file__).resolve().parents[2] / "app" / "ingestion"

    for path in ingestion_root.rglob("*.py"):
        contents = path.read_text(encoding="utf-8")
        assert "fastapi" not in contents.lower()
        assert "starlette" not in contents.lower()


def test_all_stages_have_correct_names() -> None:
    proc = _mock_processor()
    emb = _mock_embedder()
    store = _mock_store()
    storage = MagicMock(spec=StorageAdapter)

    assert ValidationStage().name == "validation"
    assert StorageStage(storage).name == "storage"
    assert ExtractionStage(proc).name == "extraction"
    assert ChunkingStage().name == "chunking"
    assert EmbeddingStage(emb).name == "embedding"
    assert IndexingStage(store).name == "indexing"
    assert MetadataStage().name == "metadata"


def test_all_stages_expose_description_and_order() -> None:
    proc = _mock_processor()
    emb = _mock_embedder()
    store = _mock_store()
    storage = MagicMock(spec=StorageAdapter)

    stages = [
        ValidationStage(),
        StorageStage(storage),
        ExtractionStage(proc),
        ChunkingStage(),
        EmbeddingStage(emb),
        IndexingStage(store),
        MetadataStage(),
    ]

    for stage in stages:
        assert isinstance(stage.description, str) and stage.description, (
            f"{stage.name} must have a non-empty description"
        )
        assert isinstance(stage.order, int) and stage.order >= 1, (
            f"{stage.name} must have a positive order"
        )

    orders = [s.order for s in stages]
    assert orders == sorted(orders), "Default stages must have strictly ascending order values"
    assert len(set(orders)) == len(orders), "Default stages must have unique order values"
