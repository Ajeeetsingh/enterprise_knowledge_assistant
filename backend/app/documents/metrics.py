"""Structured processing metrics for operational visibility."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProcessingMetrics:
    """Stage-level timing metrics captured during document ingestion.

    Maps pipeline stage durations to named fields for monitoring and
    diagnostics without Prometheus or OpenTelemetry integration.
    """

    validation_duration_ms: float | None = None
    storage_duration_ms: float | None = None
    extraction_duration_ms: float | None = None
    chunking_duration_ms: float | None = None
    embedding_duration_ms: float | None = None
    indexing_duration_ms: float | None = None
    metadata_duration_ms: float | None = None
    total_duration_ms: float = 0.0
    stage_durations: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_stage_durations(cls, stage_durations: dict[str, float]) -> ProcessingMetrics:
        """Build metrics from a stage-name → duration-ms mapping."""
        total = round(sum(stage_durations.values()), 2)
        return cls(
            validation_duration_ms=stage_durations.get("validation"),
            storage_duration_ms=stage_durations.get("storage"),
            extraction_duration_ms=stage_durations.get("extraction"),
            chunking_duration_ms=stage_durations.get("chunking"),
            embedding_duration_ms=stage_durations.get("embedding"),
            indexing_duration_ms=stage_durations.get("indexing"),
            metadata_duration_ms=stage_durations.get("metadata"),
            total_duration_ms=total,
            stage_durations=dict(stage_durations),
        )
