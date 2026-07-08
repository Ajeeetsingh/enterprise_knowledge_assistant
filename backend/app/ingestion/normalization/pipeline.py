"""Canonical normalization orchestrator."""

from __future__ import annotations

import logging
import time

from app.core.logging import get_logger, log_with_fields
from app.ingestion.normalization.boilerplate import remove_boilerplate
from app.ingestion.normalization.config import NormalizationSettings
from app.ingestion.normalization.ocr_noise import clean_ocr_noise
from app.ingestion.normalization.page_numbers import remove_page_numbers
from app.ingestion.normalization.page_segments import join_pages, split_into_pages
from app.ingestion.normalization.types import CleaningStats
from app.ingestion.normalization.unicode_cleaner import normalize_unicode
from app.ingestion.normalization.whitespace import normalize_whitespace

logger = get_logger(__name__)


class CanonicalNormalizer:
    """Transform noisy extracted text into clean canonical text before chunking."""

    def __init__(self, settings: NormalizationSettings | None = None) -> None:
        self._settings = settings or NormalizationSettings()

    @property
    def settings(self) -> NormalizationSettings:
        return self._settings

    def normalize(self, text: str) -> str:
        """Run the full canonical normalization pipeline."""
        normalized, _stats = self.normalize_with_stats(text)
        return normalized

    def normalize_with_stats(self, text: str) -> tuple[str, CleaningStats]:
        """Run normalization and return structured cleaning statistics."""
        started = time.perf_counter()
        stats = CleaningStats()

        working = text
        if self._settings.enable_unicode_cleanup:
            working, unicode_stats = normalize_unicode(working)
            stats.merge(unicode_stats)

        segments = split_into_pages(working)
        stats.pages_processed = len(segments)

        if self._settings.enable_boilerplate_removal:
            boilerplate_stats = remove_boilerplate(segments, self._settings)
            stats.merge(boilerplate_stats)

        page_number_stats = remove_page_numbers(segments)
        stats.merge(page_number_stats)

        working = join_pages(segments)

        working, whitespace_stats = normalize_whitespace(working)
        stats.merge(whitespace_stats)

        if self._settings.enable_ocr_cleanup:
            working, ocr_stats = clean_ocr_noise(working)
            stats.merge(ocr_stats)

        # Final whitespace pass ensures idempotent blank-line collapse.
        working, final_stats = normalize_whitespace(working)
        stats.merge(final_stats)

        stats.duration_ms = round((time.perf_counter() - started) * 1000, 3)

        if any(
            (
                stats.headers_removed,
                stats.footers_removed,
                stats.page_numbers_removed,
                stats.lines_normalized,
                stats.characters_removed,
            )
        ):
            log_with_fields(
                logger,
                logging.INFO,
                "Document normalization completed",
                pages_processed=stats.pages_processed,
                headers_removed=stats.headers_removed,
                footers_removed=stats.footers_removed,
                page_numbers_removed=stats.page_numbers_removed,
                lines_normalized=stats.lines_normalized,
                characters_removed=stats.characters_removed,
                duration_ms=stats.duration_ms,
            )

        return working, stats
