"""Shared types for the normalization pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CleaningStats:
    """Structured metrics from a normalization run."""

    headers_removed: int = 0
    footers_removed: int = 0
    page_numbers_removed: int = 0
    lines_normalized: int = 0
    characters_removed: int = 0
    duration_ms: float = 0.0
    pages_processed: int = 0

    def merge(self, other: CleaningStats) -> None:
        """Accumulate stats from a sub-step."""
        self.headers_removed += other.headers_removed
        self.footers_removed += other.footers_removed
        self.page_numbers_removed += other.page_numbers_removed
        self.lines_normalized += other.lines_normalized
        self.characters_removed += other.characters_removed


@dataclass
class PageSegment:
    """A single page block with its marker and body lines."""

    marker: str | None
    lines: list[str] = field(default_factory=list)
