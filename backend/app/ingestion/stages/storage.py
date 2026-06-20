"""Document storage stage."""

from __future__ import annotations

from app.documents.types import IngestionContext
from app.ingestion.stages.base import PipelineStage
from app.storage.interface import StorageAdapter


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
        saved_path = self._storage.save(context.filename, context.content)
        context.storage_path = str(saved_path)
        context.stage_results[self.name] = "stored"
        return context
