"""Document ingestion pipeline."""

from app.ingestion.pipeline import IngestionPipeline, create_default_pipeline

__all__ = ["IngestionPipeline", "create_default_pipeline"]
