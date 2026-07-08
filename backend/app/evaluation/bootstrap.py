"""Bootstrap evaluation corpora into the production ingestion pipeline."""

from __future__ import annotations

import mimetypes
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import get_settings
from app.ingestion.embedding.sentence_transformer import SentenceTransformerEmbeddingProvider
from app.ingestion.vector_store.faiss_store import FaissVectorStore
from app.services.document_service import build_document_service
from app.storage.local import LocalStorage

if TYPE_CHECKING:
    from app.embeddings.runtime import EmbeddingRuntime


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_PATH = BACKEND_ROOT.parent / "data"
CONTENT_TYPE_OVERRIDES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@dataclass(frozen=True)
class BootstrapResult:
    """Outcome of corpus bootstrap for evaluation."""

    corpus_path: Path
    indexed_documents: list[str]
    total_chunks: int
    vector_store: FaissVectorStore
    embedding_model_id: str = "minilm-l6-v2"
    embedding_model_name: str = ""
    embedding_dimension: int = 0
    model_load_ms: float = 0.0
    embedding_time_ms: float = 0.0
    index_build_ms: float = 0.0
    index_size_bytes: int = 0


def _resolve_content_type(path: Path) -> str:
    override = CONTENT_TYPE_OVERRIDES.get(path.suffix.lower())
    if override:
        return override
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _iter_corpus_files(
    corpus_path: Path,
    *,
    include_documents: list[str] | None = None,
) -> list[Path]:
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus path does not exist: {corpus_path}")

    if corpus_path.is_file():
        files = [corpus_path]
    else:
        files = sorted(
            path
            for path in corpus_path.rglob("*")
            if path.is_file() and path.suffix.lower() in CONTENT_TYPE_OVERRIDES
        )

    if include_documents:
        allowed = {name.lower() for name in include_documents}
        files = [path for path in files if path.name.lower() in allowed]

    if not files:
        raise FileNotFoundError(
            f"No supported documents found in corpus path: {corpus_path}"
        )
    return files


def bootstrap_evaluation_corpus(
    *,
    corpus_path: str | Path | None = None,
    storage_path: str | Path | None = None,
    include_documents: list[str] | None = None,
    embedding_runtime: EmbeddingRuntime | None = None,
) -> BootstrapResult:
    """Index documents through the real ingestion pipeline for benchmarking."""
    resolved_corpus = Path(corpus_path) if corpus_path else DEFAULT_CORPUS_PATH
    resolved_storage = (
        Path(storage_path)
        if storage_path
        else BACKEND_ROOT / "evaluation_storage"
    )

    bootstrap_started = time.perf_counter()

    if embedding_runtime is not None:
        vector_store = embedding_runtime.vector_store
        embedding_provider = embedding_runtime.provider
        embedding_model_id = embedding_runtime.model_id
        embedding_model_name = embedding_runtime.model_name
        embedding_manager = embedding_runtime.manager
    else:
        vector_store = FaissVectorStore()
        embedding_provider = SentenceTransformerEmbeddingProvider()
        embedding_model_id = "minilm-l6-v2"
        embedding_model_name = vector_store.model_name
        embedding_manager = vector_store._embedding_manager

    document_service = build_document_service(
        storage=LocalStorage(base_path=resolved_storage),
        vector_store=vector_store,
        embedding_provider=embedding_provider,
    )

    settings = get_settings()
    indexed_documents: list[str] = []

    preload_started = time.perf_counter()
    embedding_manager.preload()
    model_load_ms = embedding_manager.load_duration_ms or round(
        (time.perf_counter() - preload_started) * 1000,
        2,
    )

    indexing_started = time.perf_counter()
    for document_path in _iter_corpus_files(
        resolved_corpus,
        include_documents=include_documents,
    ):
        content = document_path.read_bytes()
        context = document_service.reindex_document_vectors(
            document_id=str(uuid.uuid4()),
            filename=document_path.name,
            content_type=_resolve_content_type(document_path),
            content=content,
            tenant_id=settings.tenant_id,
        )
        if not context.indexed:
            raise RuntimeError(
                f"Document failed indexing validation: {document_path.name}"
            )
        indexed_documents.append(document_path.name)

    embedding_time_ms = round((time.perf_counter() - indexing_started) * 1000, 2)
    index_build_ms = round((time.perf_counter() - bootstrap_started) * 1000, 2)

    return BootstrapResult(
        corpus_path=resolved_corpus,
        indexed_documents=indexed_documents,
        total_chunks=vector_store.size,
        vector_store=vector_store,
        embedding_model_id=embedding_model_id,
        embedding_model_name=embedding_model_name,
        embedding_dimension=vector_store.dimension or embedding_manager.dimension,
        model_load_ms=model_load_ms,
        embedding_time_ms=embedding_time_ms,
        index_build_ms=index_build_ms,
        index_size_bytes=vector_store.index_size_bytes,
    )
