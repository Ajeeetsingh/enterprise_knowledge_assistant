"""Vector index update stage."""

from __future__ import annotations

from app.core.exceptions import DocumentIngestionError
from app.documents.types import IngestionContext
from app.ingestion.stages.base import PipelineStage
from app.ingestion.vector_store.base import VectorStore


class IndexingStage(PipelineStage):
    """Add chunk embeddings to the vector store.

    Depends on the ``VectorStore`` abstraction — plugging in a different
    backend (Qdrant, pgvector, Pinecone) requires no pipeline modifications.
    """

    def __init__(self, store: VectorStore) -> None:
        self._store = store

    @property
    def name(self) -> str:
        return "indexing"

    @property
    def description(self) -> str:
        return "Add chunk embeddings to the vector store."

    @property
    def order(self) -> int:
        return 6

    def process(self, context: IngestionContext) -> IngestionContext:
        if not context.chunks:
            context.stage_results[self.name] = "skipped:no_chunks"
            return context

        if len(context.embeddings) != len(context.chunks):
            raise DocumentIngestionError(
                f"Embedding count ({len(context.embeddings)}) does not match "
                f"chunk count ({len(context.chunks)}). "
                "Ensure EmbeddingStage runs before IndexingStage."
            )

        context.vector_ids = self._store.add_chunks(
            context.chunks,
            context.embeddings,
            document_id=context.document_id,
        )
        context.indexed = True
        context.stage_results[self.name] = f"indexed:{len(context.vector_ids)}"
        return context
