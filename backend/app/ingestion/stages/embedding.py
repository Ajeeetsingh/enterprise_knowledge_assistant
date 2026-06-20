"""Embedding generation stage."""

from __future__ import annotations

from app.core.exceptions import DocumentIngestionError
from app.documents.types import IngestionContext
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.stages.base import PipelineStage


class EmbeddingStage(PipelineStage):
    """Generate dense vector embeddings for document chunks.

    Depends on the ``EmbeddingProvider`` abstraction — swapping providers
    (OpenAI, Cohere, local model) requires no pipeline modifications.
    """

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return "embedding"

    @property
    def description(self) -> str:
        return "Generate dense vector embeddings for each document chunk."

    @property
    def order(self) -> int:
        return 5

    def process(self, context: IngestionContext) -> IngestionContext:
        if not context.chunks:
            # No chunks to embed (e.g. empty document after extraction).
            context.stage_results[self.name] = "skipped:no_chunks"
            return context

        texts = [chunk.content for chunk in context.chunks]
        context.embeddings = self._provider.embed(texts)
        context.embedding_count = len(context.embeddings)
        context.stage_results[self.name] = f"embedded:{context.embedding_count}"
        return context
