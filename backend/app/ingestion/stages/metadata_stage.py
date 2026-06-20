"""Document metadata assembly stage."""

from __future__ import annotations

from app.core.exceptions import DocumentIngestionError
from app.documents.metadata import DocumentMetadata, IndexingStatus
from app.documents.types import IngestionContext
from app.ingestion.stages.base import PipelineStage


class MetadataStage(PipelineStage):
    """Assemble final document metadata after all processing stages complete."""

    @property
    def name(self) -> str:
        return "metadata"

    @property
    def description(self) -> str:
        return "Assemble final document metadata after all processing stages complete."

    @property
    def order(self) -> int:
        return 7

    def process(self, context: IngestionContext) -> IngestionContext:
        if context.checksum is None:
            raise DocumentIngestionError("Checksum is required before metadata assembly.")

        status = IndexingStatus.INDEXED if context.indexed else IndexingStatus.PENDING
        context.metadata = DocumentMetadata.create_pending(
            filename=context.filename,
            content_type=context.content_type,
            checksum=context.checksum,
            storage_path=context.storage_path,
            tenant_id=context.tenant_id,
        )
        if context.document_id is not None:
            context.metadata.document_id = context.document_id
        context.metadata.indexing_status = status
        context.stage_results[self.name] = "metadata_created"
        return context
