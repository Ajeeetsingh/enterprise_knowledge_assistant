"""Document processing outcome types for production readiness."""

from __future__ import annotations

from dataclasses import dataclass

from app.documents.metrics import ProcessingMetrics
from app.documents.progress import ProcessingProgress
from app.documents.types import IngestionResult


@dataclass(frozen=True)
class DocumentProcessingOutcome:
    """Result of a tracked ingestion run including metrics and progress."""

    result: IngestionResult
    metrics: ProcessingMetrics
    progress: ProcessingProgress
