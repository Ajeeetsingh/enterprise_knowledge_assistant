"""Embedding generation stage."""

from __future__ import annotations

import logging

from app.core.exceptions import DocumentIngestionError, EmbeddingError
from app.core.logging import get_logger, log_with_fields
from app.documents.types import IngestionContext
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.stages.base import PipelineStage

logger = get_logger(__name__)


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
        try:
            context.embeddings = self._provider.embed(texts)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                f"Embedding generation failed: {type(exc).__name__}"
            ) from exc

        context.embedding_count = len(context.embeddings)
        if context.embedding_count != len(context.chunks):
            raise DocumentIngestionError(
                "Embedding count does not match chunk count after generation."
            )
        if context.embeddings and not any(any(value for value in vector) for vector in context.embeddings):
            raise EmbeddingError("Embedding generation produced empty vectors.")

        dimension = len(context.embeddings[0]) if context.embeddings else 0
        model_name = getattr(self._provider, "_model_name", type(self._provider).__name__)
        log_with_fields(
            logger,
            logging.INFO,
            "Embedding generation completed",
            document_id=context.document_id,
            filename=context.filename,
            embedding_model=model_name,
            embedding_dimension=dimension,
            vectors_generated=context.embedding_count,
        )
        context.stage_results[self.name] = f"embedded:{context.embedding_count}"
        return context
