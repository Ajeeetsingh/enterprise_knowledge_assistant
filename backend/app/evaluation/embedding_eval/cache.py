"""Corpus fingerprinting and benchmark result caching."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.evaluation.bootstrap import BootstrapResult, _iter_corpus_files

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_DIR = BACKEND_ROOT / "evaluation_results" / "embedding_cache"


def corpus_fingerprint(
    corpus_path: str | Path,
    *,
    include_documents: list[str] | None = None,
) -> str:
    """Return a stable fingerprint for the indexed corpus."""
    resolved = Path(corpus_path)
    digest = hashlib.sha256()
    for file_path in _iter_corpus_files(resolved, include_documents=include_documents):
        stat = file_path.stat()
        digest.update(file_path.name.lower().encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(int(stat.st_mtime)).encode("utf-8"))
    return digest.hexdigest()


def cache_entry_path(
    *,
    model_id: str,
    corpus_fingerprint_value: str,
    cache_dir: str | Path | None = None,
) -> Path:
    base = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    return base / model_id / f"{corpus_fingerprint_value}.json"


def load_cached_bootstrap_metadata(
    *,
    model_id: str,
    corpus_path: str | Path,
    include_documents: list[str] | None = None,
    cache_dir: str | Path | None = None,
) -> dict | None:
    """Return cached bootstrap metadata when the corpus fingerprint matches."""
    fingerprint = corpus_fingerprint(corpus_path, include_documents=include_documents)
    path = cache_entry_path(
        model_id=model_id,
        corpus_fingerprint_value=fingerprint,
        cache_dir=cache_dir,
    )
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("corpus_fingerprint") != fingerprint:
        return None
    return payload


def save_cached_bootstrap_metadata(
    *,
    bootstrap: BootstrapResult,
    corpus_path: str | Path,
    include_documents: list[str] | None = None,
    cache_dir: str | Path | None = None,
) -> Path:
    """Persist bootstrap timing metadata for reuse across comparison runs."""
    fingerprint = corpus_fingerprint(corpus_path, include_documents=include_documents)
    path = cache_entry_path(
        model_id=bootstrap.embedding_model_id,
        corpus_fingerprint_value=fingerprint,
        cache_dir=cache_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "corpus_fingerprint": fingerprint,
        "embedding_model_id": bootstrap.embedding_model_id,
        "embedding_model_name": bootstrap.embedding_model_name,
        "embedding_dimension": bootstrap.embedding_dimension,
        "model_load_ms": bootstrap.model_load_ms,
        "index_build_ms": bootstrap.index_build_ms,
        "embedding_time_ms": bootstrap.embedding_time_ms,
        "index_size_bytes": bootstrap.index_size_bytes,
        "total_chunks": bootstrap.total_chunks,
        "indexed_documents": bootstrap.indexed_documents,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
