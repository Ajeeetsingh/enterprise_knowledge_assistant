"""Post-index retrieval validation stage."""

from __future__ import annotations

import logging

from app.core.exceptions import DocumentIngestionError
from app.core.logging import get_logger, log_with_fields
from app.documents.types import IngestionContext
from app.ingestion.stages.base import PipelineStage
from app.ingestion.vector_store.base import VectorStore
from app.ingestion.vector_store.faiss_store import FaissVectorStore

logger = get_logger(__name__)


def _validation_query(context: IngestionContext) -> str:
    """Build a short phrase from indexed content for smoke retrieval."""
    if context.chunks:
        words = context.chunks[0].content.split()
        return " ".join(words[:8])
    if context.extracted_text:
        words = context.extracted_text.split()
        return " ".join(words[:8])
    return ""


class IndexValidationStage(PipelineStage):
    """Verify indexed chunks are retrievable before marking a document searchable."""

    def __init__(
        self,
        store: VectorStore,
        *,
        min_hits: int = 1,
        min_score: float = 0.05,
    ) -> None:
        self._store = store
        self._min_hits = min_hits
        self._min_score = min_score

    @property
    def name(self) -> str:
        return "index_validation"

    @property
    def description(self) -> str:
        return "Validate semantic retrieval against freshly indexed chunks."

    @property
    def order(self) -> int:
        return 7

    def process(self, context: IngestionContext) -> IngestionContext:
        if not isinstance(self._store, FaissVectorStore):
            context.stage_results[self.name] = "skipped:unsupported_store"
            return context

        if not context.indexed or not context.chunks:
            context.stage_results[self.name] = "skipped:not_indexed"
            return context

        query = _validation_query(context)
        if not query:
            context.indexed = False
            raise DocumentIngestionError(
                "Index validation failed: no validation query could be derived."
            )

        results = self._store.search(
            query,
            top_k=3,
            allowed_sources={context.filename},
            min_score=self._min_score,
        )
        matching = [result for result in results if result.source == context.filename]

        log_with_fields(
            logger,
            logging.INFO,
            "Index validation completed",
            document_id=context.document_id,
            filename=context.filename,
            validation_query=query,
            hits=len(matching),
            top_score=matching[0].confidence if matching else 0.0,
        )

        if len(matching) < self._min_hits:
            context.indexed = False
            raise DocumentIngestionError(
                "Index validation failed: uploaded document is not retrievable "
                f"via semantic search (query={query!r})."
            )

        context.stage_results[self.name] = f"validated:{len(matching)}"
        return context
