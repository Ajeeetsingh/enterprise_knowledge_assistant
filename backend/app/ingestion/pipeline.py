"""Document ingestion pipeline abstraction and default implementation."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

from app.core.exceptions import DocumentIngestionError, ServiceError
from app.core.logging import get_logger, log_with_fields
from app.documents.types import IngestionContext, IngestionResult
from app.ingestion.stages import (
    ChunkingStage,
    EmbeddingStage,
    ExtractionStage,
    IndexValidationStage,
    IndexingStage,
    MetadataStage,
    PipelineStage,
    StorageStage,
    ValidationStage,
)
from app.ingestion.embedding.base import EmbeddingProvider
from app.ingestion.processor import DocumentProcessor
from app.ingestion.vector_store.base import VectorStore
from app.storage.interface import StorageAdapter

logger = get_logger(__name__)


class IngestionPipelineBase(ABC):
    """Abstract ingestion pipeline contract.

    Future pipeline variants (async, bulk, OCR, cloud) implement this
    interface.  ``DocumentService`` depends only on this abstraction.
    """

    @property
    @abstractmethod
    def stage_names(self) -> list[str]:
        """Return ordered stage identifiers."""

    @property
    def stages(self) -> list[PipelineStage]:
        """Return ordered stage instances when available."""
        return []

    @abstractmethod
    def run(self, context: IngestionContext) -> IngestionResult:
        """Execute the pipeline and return an ``IngestionResult``."""


class IngestionPipeline(IngestionPipelineBase):
    """Sequential pipeline that runs ordered ``PipelineStage`` instances.

    Each stage receives the ``IngestionContext`` produced by the previous
    stage, enriching it until the final ``IngestionResult`` is assembled.
    """

    def __init__(self, stages: list[PipelineStage]) -> None:
        if not stages:
            raise DocumentIngestionError("Ingestion pipeline requires at least one stage.")
        self._stages = stages

    @property
    def stage_names(self) -> list[str]:
        return [stage.name for stage in self._stages]

    @property
    def stages(self) -> list[PipelineStage]:
        return list(self._stages)

    def run(self, context: IngestionContext) -> IngestionResult:
        current = context
        log_with_fields(
            logger,
            logging.INFO,
            "Ingestion pipeline started",
            filename=current.filename,
            stage_count=len(self._stages),
        )

        for stage in self._stages:
            log_with_fields(
                logger,
                logging.INFO,
                "Pipeline stage started",
                stage=stage.name,
                filename=current.filename,
            )
            stage_start = time.perf_counter()
            try:
                current = stage.process(current)
            except ServiceError:
                duration_ms = round((time.perf_counter() - stage_start) * 1000, 2)
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "Pipeline stage failed",
                    stage=stage.name,
                    filename=current.filename,
                    document_id=current.document_id,
                    duration_ms=duration_ms,
                )
                raise
            except Exception as exc:
                duration_ms = round((time.perf_counter() - stage_start) * 1000, 2)
                log_with_fields(
                    logger,
                    logging.ERROR,
                    "Pipeline stage failed",
                    stage=stage.name,
                    filename=current.filename,
                    document_id=current.document_id,
                    reason=type(exc).__name__,
                    duration_ms=duration_ms,
                )
                raise DocumentIngestionError(
                    f"Pipeline stage '{stage.name}' failed."
                ) from exc

            duration_ms = round((time.perf_counter() - stage_start) * 1000, 2)
            current.stage_durations[stage.name] = duration_ms
            log_with_fields(
                logger,
                logging.INFO,
                "Pipeline stage completed",
                stage=stage.name,
                filename=current.filename,
                document_id=current.document_id,
                duration_ms=duration_ms,
            )

        log_with_fields(
            logger,
            logging.INFO,
            "Ingestion pipeline completed",
            filename=current.filename,
            document_id=current.document_id,
            total_duration_ms=round(sum(current.stage_durations.values()), 2),
        )
        return IngestionResult.from_context(current)


# Backward-compatible alias used by Phase 4.1 tests and existing imports.
DefaultIngestionPipeline = IngestionPipeline


def create_default_pipeline(
    storage: StorageAdapter,
    processor: DocumentProcessor | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store: VectorStore | None = None,
) -> IngestionPipeline:
    """Build the default ordered ingestion pipeline with working stages."""
    from app.embeddings.manager import get_embedding_manager
    from app.ingestion.processor import DefaultDocumentProcessor
    from app.ingestion.embedding.sentence_transformer import SentenceTransformerEmbeddingProvider
    from app.ingestion.vector_store.faiss_store import FaissVectorStore

    resolved_processor = processor or DefaultDocumentProcessor()
    shared_manager = get_embedding_manager()
    resolved_embedder = embedding_provider or SentenceTransformerEmbeddingProvider(
        embedding_manager=shared_manager,
    )
    resolved_store = vector_store or FaissVectorStore(embedding_manager=shared_manager)

    stages: list[PipelineStage] = [
        ValidationStage(),
        StorageStage(storage),
        ExtractionStage(resolved_processor),
        ChunkingStage(),
        EmbeddingStage(resolved_embedder),
        IndexingStage(resolved_store),
        IndexValidationStage(resolved_store),
        MetadataStage(),
    ]
    return IngestionPipeline(stages)
