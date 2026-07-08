"""Configuration for document normalization."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings, get_settings

PAGE_MARKER_PREFIX = "<<<PAGE:"


@dataclass(frozen=True)
class NormalizationSettings:
    """Configurable thresholds for the canonical normalization pipeline."""

    enable_boilerplate_removal: bool = True
    enable_unicode_cleanup: bool = True
    enable_ocr_cleanup: bool = True
    minimum_header_frequency: int = 2
    minimum_footer_frequency: int = 2
    maximum_header_lines: int = 4
    maximum_footer_lines: int = 3
    boilerplate_min_page_ratio: float = 0.4

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> NormalizationSettings:
        """Build normalization settings from application config."""
        resolved = settings or get_settings()
        return cls(
            enable_boilerplate_removal=resolved.normalization_enable_boilerplate_removal,
            enable_unicode_cleanup=resolved.normalization_enable_unicode_cleanup,
            enable_ocr_cleanup=resolved.normalization_enable_ocr_cleanup,
            minimum_header_frequency=resolved.normalization_minimum_header_frequency,
            minimum_footer_frequency=resolved.normalization_minimum_footer_frequency,
            maximum_header_lines=resolved.normalization_maximum_header_lines,
            maximum_footer_lines=resolved.normalization_maximum_footer_lines,
            boilerplate_min_page_ratio=resolved.normalization_boilerplate_min_page_ratio,
        )
