"""Base contract for ingestion pipeline stages."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.documents.types import IngestionContext


class PipelineStage(ABC):
    """A single step in the document ingestion pipeline.

    Each concrete stage exposes three pieces of immutable metadata that
    describe it without executing it:

    ``name``        — stable snake_case identifier used for logging and
                      ``stage_results`` keys.
    ``description`` — human-readable sentence explaining the stage's purpose;
                      intended for pipeline visualisation, progress reporting,
                      and diagnostics.
    ``order``       — 1-based integer reflecting the stage's canonical
                      position in the default pipeline.  Custom pipelines may
                      reorder stages; this value documents intent, it is not
                      enforced by the runtime.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable snake_case stage identifier."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this stage does."""

    @property
    @abstractmethod
    def order(self) -> int:
        """Canonical 1-based position in the default pipeline."""

    @abstractmethod
    def process(self, context: IngestionContext) -> IngestionContext:
        """Execute the stage and return the enriched context."""
