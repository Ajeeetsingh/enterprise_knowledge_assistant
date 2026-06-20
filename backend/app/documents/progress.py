"""Document processing progress tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class _StageMetadataLike(Protocol):
    name: str
    description: str
    order: int


@dataclass(frozen=True)
class ProcessingProgress:
    """Lightweight snapshot of ingestion pipeline progress.

    Designed for future async processing dashboards and polling endpoints.
    No WebSockets or SSE — just structured data.
    """

    current_stage: str | None
    completed_stages: list[str]
    total_stages: int
    progress_percentage: float

    @classmethod
    def from_stage_durations(
        cls,
        stages: list[_StageMetadataLike],
        stage_durations: dict[str, float],
        *,
        failed_stage: str | None = None,
    ) -> ProcessingProgress:
        """Build progress from completed stage timing keys."""
        ordered_names = [stage.name for stage in sorted(stages, key=lambda s: s.order)]
        total = len(ordered_names)
        completed = [name for name in ordered_names if name in stage_durations]
        current = failed_stage
        if current is None and len(completed) < total:
            remaining = [name for name in ordered_names if name not in completed]
            current = remaining[0] if remaining else None
        percentage = round((len(completed) / total) * 100, 2) if total else 0.0
        return cls(
            current_stage=current,
            completed_stages=completed,
            total_stages=total,
            progress_percentage=percentage,
        )

    @classmethod
    def completed(cls, stages: list[_StageMetadataLike]) -> ProcessingProgress:
        """Build a fully completed progress snapshot."""
        ordered_names = [stage.name for stage in sorted(stages, key=lambda s: s.order)]
        total = len(ordered_names)
        return cls(
            current_stage=None,
            completed_stages=ordered_names,
            total_stages=total,
            progress_percentage=100.0 if total else 0.0,
        )
