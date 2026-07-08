"""Configuration for document structure extraction."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings


@dataclass(frozen=True)
class StructureExtractionSettings:
    """Configurable thresholds for structure extraction."""

    enabled: bool = True
    max_heading_length: int = 200
    min_table_columns: int = 2
    min_table_rows: int = 2
    max_table_columns: int = 6
    max_stacked_table_rows: int = 25
    table_column_gap_spaces: int = 2
    table_confidence_threshold: float = 0.55
    max_list_nesting_depth: int = 6

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> StructureExtractionSettings:
        """Build structure settings from application config."""
        resolved = settings or get_settings()
        return cls(
            enabled=resolved.structure_extraction_enabled,
            max_heading_length=resolved.structure_max_heading_length,
            min_table_columns=resolved.structure_min_table_columns,
            min_table_rows=resolved.structure_min_table_rows,
            max_table_columns=resolved.structure_max_table_columns,
            max_stacked_table_rows=resolved.structure_max_stacked_table_rows,
            table_column_gap_spaces=resolved.structure_table_column_gap_spaces,
            table_confidence_threshold=resolved.structure_table_confidence_threshold,
            max_list_nesting_depth=resolved.structure_max_list_nesting_depth,
        )
