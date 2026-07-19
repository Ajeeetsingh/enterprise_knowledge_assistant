"""Document storage stage."""

from __future__ import annotations

from pathlib import Path

from app.core.exceptions import StorageError
from app.documents.types import IngestionContext
from app.ingestion.stages.base import PipelineStage
from app.storage.interface import StorageAdapter


def _storage_key(context: IngestionContext) -> str:
    """Build a confined storage key that never uses the raw upload path."""
    ext = Path(context.filename).suffix.lower()
    if context.document_id:
        return f"{context.document_id}{ext}"

    # Fallback for pipelines that have not assigned a document id yet.
    name = Path(context.filename).name
    if not name or name in {".", ".."}:
        raise StorageError("Invalid upload filename.")
    return name


class StorageStage(PipelineStage):
    """Persist raw document bytes via the configured ``StorageAdapter``."""

    def __init__(self, storage: StorageAdapter) -> None:
        self._storage = storage

    @property
    def name(self) -> str:
        return "storage"

    @property
    def description(self) -> str:
        return "Persist raw document bytes to the configured storage backend."

    @property
    def order(self) -> int:
        return 2

    def process(self, context: IngestionContext) -> IngestionContext:
        storage_key = _storage_key(context)
        saved_path = self._storage.save(storage_key, context.content)
        # Persist the absolute path returned by the adapter (existing contract).
        context.storage_path = str(saved_path)
        context.stage_results[self.name] = "stored"
        return context
