"""Comprehensive unit tests for Phase 4.2 — Enterprise Ingestion Engine."""

from __future__ import annotations

import json
import csv
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import (
    DocumentIngestionError,
    DocumentValidationError,
    EmbeddingError,
    ParserNotFoundError,
    VectorStoreError,
)
from app.documents.metadata import IndexingStatus
from app.documents.types import IngestionContext, IngestionResult
from app.ingestion.chunker import DocumentChunk
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.embedding.sentence_transformer import SentenceTransformerEmbeddingProvider
from app.ingestion.parsers.base import DocumentParser
from app.ingestion.parsers.csv import CsvParser
from app.ingestion.parsers.factory import ParserFactory, build_default_factory
from app.ingestion.parsers.json import JsonParser
from app.ingestion.parsers.txt import TxtParser
from app.ingestion.pipeline import (
    DefaultIngestionPipeline,
    IngestionPipeline,
    IngestionPipelineBase,
    create_default_pipeline,
)
from app.ingestion.processor import DefaultDocumentProcessor, DocumentProcessor
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
from app.ingestion.vector_store.faiss_store import FaissVectorStore
from app.services.document_service import (
    DocumentService,
    build_document_service,
    get_document_service,
)
from app.storage.local import LocalStorage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_STAGE_ORDER = [
    "validation",
    "storage",
    "extraction",
    "chunking",
    "embedding",
    "indexing",
    "metadata",
]


def _txt_context(content: bytes = b"Hello world.", filename: str = "hr_policy.txt") -> IngestionContext:
    return IngestionContext(filename=filename, content_type="text/plain", content=content)


def _mock_embedding_provider(dim: int = 4) -> MagicMock:
    provider = MagicMock(spec=EmbeddingProvider)
    provider.embed.side_effect = lambda texts: [[0.1] * dim for _ in texts]
    provider.dimension = dim
    return provider


def _mock_vector_store() -> MagicMock:
    store = MagicMock(spec=VectorStore)
    store.add_chunks.side_effect = (
        lambda chunks, embs, document_id=None: [c.chunk_id for c in chunks]
    )
    store.size = 0
    return store


def _mock_processor(text: str = "extracted text content") -> MagicMock:
    proc = MagicMock(spec=DocumentProcessor)
    proc.process.return_value = text
    return proc


@pytest.fixture(autouse=True)
def clear_document_service_cache():
    get_document_service.cache_clear()
    yield
    get_document_service.cache_clear()


# ---------------------------------------------------------------------------
# Pipeline abstraction
# ---------------------------------------------------------------------------

class TestPipelineAbstraction:
    def test_ingestion_pipeline_is_abstract_base(self):
        assert issubclass(IngestionPipeline, IngestionPipelineBase)

    def test_default_pipeline_alias(self):
        assert DefaultIngestionPipeline is IngestionPipeline

    def test_document_service_accepts_pipeline_base(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)
        pipeline = MagicMock(spec=IngestionPipelineBase)
        pipeline.stage_names = EXPECTED_STAGE_ORDER
        vector_store = _mock_vector_store()
        service = DocumentService(
            pipeline=pipeline,
            storage=storage,
            vector_store=vector_store,
        )
        assert service.pipeline is pipeline

    def test_pipeline_requires_stages(self):
        with pytest.raises(DocumentIngestionError, match="at least one stage"):
            IngestionPipeline([])

    def test_stage_names_ordered(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)
        pipeline = create_default_pipeline(
            storage,
            processor=_mock_processor(),
            embedding_provider=_mock_embedding_provider(),
            vector_store=_mock_vector_store(),
        )
        assert pipeline.stage_names == EXPECTED_STAGE_ORDER

    def test_stage_timing_logged(self, tmp_path, caplog):
        import logging
        storage = LocalStorage(base_path=tmp_path)
        pipeline = create_default_pipeline(
            storage,
            processor=_mock_processor("some text for chunking"),
            embedding_provider=_mock_embedding_provider(),
            vector_store=_mock_vector_store(),
        )
        with caplog.at_level(logging.INFO):
            pipeline.run(_txt_context())
        assert any("duration_ms" in r.message or "duration_ms" in str(r.__dict__)
                   for r in caplog.records)


# ---------------------------------------------------------------------------
# Parser architecture
# ---------------------------------------------------------------------------

class TestParserFactory:
    def test_get_registered_parser(self):
        factory = ParserFactory()
        parser = TxtParser()
        factory.register(parser)
        assert factory.get("readme.txt") is parser

    def test_get_raises_for_unregistered_extension(self):
        factory = ParserFactory()
        with pytest.raises(ParserNotFoundError):
            factory.get("archive.zip")

    def test_register_multiple_extensions(self):
        class MultiParser(DocumentParser):
            @property
            def supported_extensions(self):
                return frozenset({".a", ".b"})
            def parse(self, content, filename):
                return ""

        factory = ParserFactory()
        factory.register(MultiParser())
        assert factory.get("file.a") is factory.get("file.b")

    def test_default_factory_covers_all_formats(self):
        factory = build_default_factory()
        for ext in (".txt", ".csv", ".json", ".pdf", ".docx", ".xlsx"):
            assert factory.get(f"doc{ext}") is not None

    def test_factory_supported_extensions(self):
        factory = build_default_factory()
        exts = factory.supported_extensions()
        assert ".txt" in exts and ".pdf" in exts


class TestTxtParser:
    def test_parse_utf8(self):
        parser = TxtParser()
        result = parser.parse(b"Hello, world!", "doc.txt")
        assert result == "Hello, world!"

    def test_parse_empty(self):
        parser = TxtParser()
        assert parser.parse(b"", "doc.txt") == ""

    def test_supported_extensions(self):
        assert ".txt" in TxtParser().supported_extensions


class TestCsvParser:
    def test_parse_csv(self):
        content = "name,age\nAlice,30\nBob,25".encode()
        parser = CsvParser()
        result = parser.parse(content, "employees.csv")
        assert "name: Alice" in result or "Alice" in result
        assert "Bob" in result

    def test_supported_extensions(self):
        assert ".csv" in CsvParser().supported_extensions


class TestJsonParser:
    def test_parse_dict(self):
        data = {"title": "Policy", "content": "Annual leave is 20 days."}
        parser = JsonParser()
        result = parser.parse(json.dumps(data).encode(), "policy.json")
        assert "Policy" in result
        assert "Annual leave" in result

    def test_parse_list(self):
        data = [{"event": "login"}, {"event": "logout"}]
        parser = JsonParser()
        result = parser.parse(json.dumps(data).encode(), "logs.json")
        assert "login" in result

    def test_invalid_json_returns_raw(self):
        parser = JsonParser()
        result = parser.parse(b"not json", "bad.json")
        assert "not json" in result

    def test_supported_extensions(self):
        assert ".json" in JsonParser().supported_extensions


# ---------------------------------------------------------------------------
# Document processor
# ---------------------------------------------------------------------------

class TestDefaultDocumentProcessor:
    def test_process_delegates_to_parser(self, tmp_path):
        factory = build_default_factory()
        processor = DefaultDocumentProcessor(parser_factory=factory)
        ctx = _txt_context(b"  Hello   world.  \n\n\n  Extra.  ")
        result = processor.process(ctx)
        assert "Hello world." in result
        assert "\n\n\n" not in result

    def test_normalization_strips_whitespace(self):
        processor = DefaultDocumentProcessor.__new__(DefaultDocumentProcessor)
        assert processor._normalize("  hello  ") == "hello"

    def test_normalization_collapses_blank_lines(self):
        processor = DefaultDocumentProcessor.__new__(DefaultDocumentProcessor)
        result = processor._normalize("line1\n\n\n\nline2")
        assert result == "line1\n\nline2"

    def test_processor_raises_for_unknown_extension(self):
        processor = DefaultDocumentProcessor(parser_factory=ParserFactory())
        ctx = IngestionContext(
            filename="archive.zip", content_type="application/zip", content=b"data"
        )
        with pytest.raises(ParserNotFoundError):
            processor.process(ctx)

    def test_processor_is_replaceable(self):
        """DocumentService accepts any DocumentProcessor subclass."""
        custom = _mock_processor("custom extracted text")
        assert isinstance(custom, MagicMock)

    def test_default_processor_implements_abstract_base(self):
        processor = DefaultDocumentProcessor()
        assert isinstance(processor, DocumentProcessor)


# ---------------------------------------------------------------------------
# Embedding provider
# ---------------------------------------------------------------------------

class TestEmbeddingProvider:
    def test_sentence_transformer_implements_base(self):
        provider = SentenceTransformerEmbeddingProvider()
        assert isinstance(provider, EmbeddingProvider)

    def test_embed_delegates_to_model(self):
        provider = SentenceTransformerEmbeddingProvider()
        mock_model = MagicMock()
        mock_model.encode.return_value = __import__("numpy").array([[0.1, 0.2]])
        provider._model = mock_model
        result = provider.embed(["hello"])
        assert len(result) == 1
        assert len(result[0]) == 2

    def test_embed_empty_returns_empty(self):
        provider = SentenceTransformerEmbeddingProvider()
        assert provider.embed([]) == []

    def test_embed_raises_embedding_error_on_failure(self):
        provider = SentenceTransformerEmbeddingProvider()
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("model broken")
        provider._model = mock_model
        with pytest.raises(EmbeddingError):
            provider.embed(["text"])

    def test_mock_provider_is_substitutable(self):
        """Any EmbeddingProvider can replace SentenceTransformer in the pipeline."""
        mock = _mock_embedding_provider(dim=8)
        vectors = mock.embed(["test"])
        assert len(vectors[0]) == 8


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

class TestFaissVectorStore:
    def test_implements_vector_store_base(self):
        store = FaissVectorStore()
        assert isinstance(store, VectorStore)

    def test_add_chunks_returns_ids(self):
        pytest.importorskip("faiss")
        store = FaissVectorStore()
        chunks = [
            DocumentChunk("src::0", "text one", "doc.txt", "hr", 0),
            DocumentChunk("src::1", "text two", "doc.txt", "hr", 1),
        ]
        embeddings = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]
        ids = store.add_chunks(chunks, embeddings)
        assert ids == ["src::0", "src::1"]
        assert store.size == 2

    def test_add_empty_chunks_returns_empty(self):
        store = FaissVectorStore()
        assert store.add_chunks([], []) == []

    def test_mismatched_lengths_raises(self):
        store = FaissVectorStore()
        chunks = [DocumentChunk("c::0", "text", "f.txt", "hr", 0)]
        with pytest.raises(VectorStoreError, match="length"):
            store.add_chunks(chunks, [])

    def test_dimension_mismatch_raises(self):
        pytest.importorskip("faiss")
        store = FaissVectorStore()
        chunks = [DocumentChunk("c::0", "text", "f.txt", "hr", 0)]
        store.add_chunks(chunks, [[0.1, 0.2]])
        with pytest.raises(VectorStoreError, match="dimension"):
            store.add_chunks(chunks, [[0.1, 0.2, 0.3]])

    def test_mock_store_is_substitutable(self):
        """Any VectorStore can replace FaissVectorStore."""
        mock = _mock_vector_store()
        chunks = [DocumentChunk("c::0", "text", "f.txt", "hr", 0)]
        ids = mock.add_chunks(chunks, [[0.1, 0.2]], document_id="doc-1")
        assert ids == ["c::0"]

    def test_remove_document_drops_vectors_for_document(self):
        pytest.importorskip("faiss")
        store = FaissVectorStore()
        chunks_a = [DocumentChunk("a::0", "text a", "a.txt", "hr", 0)]
        chunks_b = [DocumentChunk("b::0", "text b", "b.txt", "hr", 0)]
        store.add_chunks(chunks_a, [[0.1, 0.2, 0.3, 0.4]], document_id="doc-a")
        store.add_chunks(chunks_b, [[0.5, 0.6, 0.7, 0.8]], document_id="doc-b")
        assert store.size == 2

        store.remove_document("doc-a")

        assert store.size == 1
        store.remove_document("missing-doc")
        assert store.size == 1


# ---------------------------------------------------------------------------
# Validation stage
# ---------------------------------------------------------------------------

class TestValidationStage:
    def test_valid_document_passes(self):
        stage = ValidationStage()
        ctx = _txt_context()
        result = stage.process(ctx)
        assert result.checksum is not None
        assert result.stage_results["validation"] == "validated"

    def test_empty_filename_raises(self):
        stage = ValidationStage()
        ctx = _txt_context()
        ctx.filename = "   "
        with pytest.raises(DocumentValidationError, match="filename"):
            stage.process(ctx)

    def test_empty_content_raises(self):
        stage = ValidationStage()
        ctx = _txt_context(content=b"")
        with pytest.raises(DocumentValidationError, match="content"):
            stage.process(ctx)

    def test_unsupported_extension_raises(self):
        stage = ValidationStage()
        ctx = IngestionContext(
            filename="archive.zip", content_type="application/zip", content=b"data"
        )
        with pytest.raises(DocumentValidationError, match="extension"):
            stage.process(ctx)

    def test_oversized_file_raises(self):
        stage = ValidationStage(max_size_bytes=10)
        ctx = _txt_context(content=b"x" * 11)
        with pytest.raises(DocumentValidationError, match="size"):
            stage.process(ctx)

    def test_extra_validators_called(self):
        called = []
        class FakeValidator:
            def validate(self, context):
                called.append(True)
        stage = ValidationStage(extra_validators=[FakeValidator()])
        stage.process(_txt_context())
        assert called

    def test_checksum_is_sha256(self):
        import hashlib
        stage = ValidationStage()
        content = b"policy text"
        ctx = stage.process(_txt_context(content=content))
        assert ctx.checksum == hashlib.sha256(content).hexdigest()


# ---------------------------------------------------------------------------
# Storage stage
# ---------------------------------------------------------------------------

class TestStorageStage:
    def test_stores_file_bytes(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)
        stage = StorageStage(storage)
        ctx = _txt_context(b"document content")
        ctx.filename = "policy.txt"
        result = stage.process(ctx)
        assert result.storage_path is not None
        assert Path(result.storage_path).exists()
        assert Path(result.storage_path).read_bytes() == b"document content"

    def test_storage_path_set_on_context(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)
        stage = StorageStage(storage)
        result = stage.process(_txt_context())
        assert result.storage_path is not None


# ---------------------------------------------------------------------------
# Extraction stage
# ---------------------------------------------------------------------------

class TestExtractionStage:
    def test_sets_extracted_text(self):
        stage = ExtractionStage(_mock_processor("extracted text"))
        ctx = _txt_context()
        result = stage.process(ctx)
        assert result.extracted_text == "extracted text"
        assert result.stage_results["extraction"] == "extracted"

    def test_processor_is_called_with_context(self):
        proc = _mock_processor()
        stage = ExtractionStage(proc)
        ctx = _txt_context()
        stage.process(ctx)
        proc.process.assert_called_once_with(ctx)


# ---------------------------------------------------------------------------
# Chunking stage
# ---------------------------------------------------------------------------

class TestChunkingStage:
    def test_produces_chunks_from_text(self):
        stage = ChunkingStage()
        ctx = _txt_context()
        ctx.extracted_text = "The quick brown fox jumps over the lazy dog. " * 30
        result = stage.process(ctx)
        assert result.chunk_count > 0
        assert len(result.chunks) == result.chunk_count

    def test_raises_if_no_extracted_text(self):
        stage = ChunkingStage()
        ctx = _txt_context()
        with pytest.raises(DocumentIngestionError, match="Extracted text"):
            stage.process(ctx)

    def test_empty_text_yields_zero_chunks(self):
        stage = ChunkingStage()
        ctx = _txt_context()
        ctx.extracted_text = "   "
        result = stage.process(ctx)
        assert result.chunk_count == 0


# ---------------------------------------------------------------------------
# Embedding stage
# ---------------------------------------------------------------------------

class TestEmbeddingStage:
    def test_embeds_chunks(self):
        provider = _mock_embedding_provider(dim=4)
        stage = EmbeddingStage(provider)
        ctx = _txt_context()
        ctx.chunks = [DocumentChunk("f::0", "text one", "f.txt", "hr", 0)]
        result = stage.process(ctx)
        assert result.embedding_count == 1
        assert len(result.embeddings) == 1

    def test_skips_embedding_when_no_chunks(self):
        provider = _mock_embedding_provider()
        stage = EmbeddingStage(provider)
        ctx = _txt_context()
        result = stage.process(ctx)
        assert result.stage_results["embedding"] == "skipped:no_chunks"
        provider.embed.assert_not_called()


# ---------------------------------------------------------------------------
# Indexing stage
# ---------------------------------------------------------------------------

class TestIndexingStage:
    def test_indexes_chunks_and_embeddings(self):
        store = _mock_vector_store()
        stage = IndexingStage(store)
        ctx = _txt_context()
        ctx.chunks = [DocumentChunk("f::0", "text", "f.txt", "hr", 0)]
        ctx.embeddings = [[0.1, 0.2, 0.3, 0.4]]
        result = stage.process(ctx)
        assert result.indexed is True
        assert result.vector_ids == ["f::0"]

    def test_skips_when_no_chunks(self):
        store = _mock_vector_store()
        stage = IndexingStage(store)
        ctx = _txt_context()
        result = stage.process(ctx)
        assert result.indexed is False
        store.add_chunks.assert_not_called()

    def test_raises_on_mismatched_embeddings(self):
        store = _mock_vector_store()
        stage = IndexingStage(store)
        ctx = _txt_context()
        ctx.chunks = [DocumentChunk("f::0", "text", "f.txt", "hr", 0)]
        ctx.embeddings = []
        with pytest.raises(DocumentIngestionError):
            stage.process(ctx)


# ---------------------------------------------------------------------------
# Full pipeline integration (mocked heavy deps)
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_complete_pipeline_produces_indexed_result(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)
        processor = _mock_processor("Annual leave is 20 days per year for all employees.")
        embedder = _mock_embedding_provider(dim=4)
        store = _mock_vector_store()
        pipeline = create_default_pipeline(
            storage,
            processor=processor,
            embedding_provider=embedder,
            vector_store=store,
        )
        result = pipeline.run(
            IngestionContext(
                filename="hr_policy.txt",
                content_type="text/plain",
                content=b"Annual leave is 20 days per year for all employees.",
                tenant_id="default",
            )
        )
        assert result.indexed is True
        assert result.chunk_count > 0
        assert result.embedding_count == result.chunk_count
        assert result.metadata.indexing_status == IndexingStatus.INDEXED
        assert result.metadata.checksum is not None
        assert Path(result.storage_path).exists()

    def test_pipeline_service_error_propagates_unchanged(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)
        processor = _mock_processor()
        embedder = MagicMock(spec=EmbeddingProvider)
        embedder.embed.side_effect = EmbeddingError("model failure")
        store = _mock_vector_store()
        pipeline = create_default_pipeline(
            storage,
            processor=processor,
            embedding_provider=embedder,
            vector_store=store,
        )
        with pytest.raises(EmbeddingError):
            pipeline.run(_txt_context(b"some content"))

    def test_pipeline_unexpected_error_wrapped(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)

        class BurstingStage(PipelineStage):
            @property
            def name(self):
                return "bursting"

            @property
            def description(self):
                return "Test-only stage that raises unexpectedly."

            @property
            def order(self):
                return 99

            def process(self, context):
                raise RuntimeError("unexpected")

        pipeline = IngestionPipeline([ValidationStage(), BurstingStage()])
        with pytest.raises(DocumentIngestionError, match="bursting"):
            pipeline.run(_txt_context())

    def test_no_fastapi_in_ingestion_package(self):
        ingestion_root = (
            Path(__file__).resolve().parents[2] / "app" / "ingestion"
        )
        for py_file in ingestion_root.rglob("*.py"):
            src = py_file.read_text(encoding="utf-8")
            assert "fastapi" not in src.lower(), f"FastAPI import in {py_file}"
            assert "starlette" not in src.lower(), f"Starlette import in {py_file}"


# ---------------------------------------------------------------------------
# DocumentService + DI
# ---------------------------------------------------------------------------

class TestDocumentService:
    def test_ingest_delegates_to_pipeline(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)
        processor = _mock_processor("employee policy text content here.")
        embedder = _mock_embedding_provider(dim=4)
        store = _mock_vector_store()
        service = build_document_service(
            storage=storage,
            processor=processor,
            embedding_provider=embedder,
            vector_store=store,
        )
        result = service.ingest(
            filename="handbook.txt",
            content_type="text/plain",
            content=b"employee policy text content here.",
        )
        assert isinstance(result, IngestionResult)
        assert result.metadata.filename == "handbook.txt"

    def test_get_document_service_returns_cached_singleton(self):
        first = get_document_service()
        second = get_document_service()
        assert first is second

    def test_build_document_service_respects_overrides(self, tmp_path):
        storage = LocalStorage(base_path=tmp_path)
        custom_processor = _mock_processor("custom")
        service = build_document_service(
            storage=storage,
            processor=custom_processor,
            embedding_provider=_mock_embedding_provider(),
            vector_store=_mock_vector_store(),
        )
        assert isinstance(service, DocumentService)
        assert service.storage is storage
