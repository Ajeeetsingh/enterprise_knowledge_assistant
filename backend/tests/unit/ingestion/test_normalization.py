"""Unit tests for Phase 12.3A document normalization pipeline."""

from __future__ import annotations

import pytest

from app.ingestion.normalization import CanonicalNormalizer, NormalizationSettings
from app.ingestion.normalization.boilerplate import remove_boilerplate
from app.ingestion.normalization.ocr_noise import clean_ocr_noise
from app.ingestion.normalization.page_numbers import remove_page_numbers
from app.ingestion.normalization.page_segments import (
    boilerplate_line_key,
    join_pages,
    split_into_pages,
)
from app.ingestion.normalization.unicode_cleaner import normalize_unicode
from app.ingestion.normalization.whitespace import normalize_whitespace
from app.ingestion.processor import DefaultDocumentProcessor


def _settings(**overrides) -> NormalizationSettings:
    return NormalizationSettings(**overrides)


def _multi_page_text(pages: list[tuple[str, list[str]]]) -> str:
    blocks: list[str] = []
    for marker, lines in pages:
        blocks.append(marker)
        blocks.extend(lines)
    return "\n".join(blocks)


class TestPageSegments:
    def test_split_and_join_preserves_markers(self):
        text = "<<<PAGE:1>>>\nLine A\n<<<PAGE:2>>>\nLine B"
        segments = split_into_pages(text)
        assert len(segments) == 2
        assert segments[0].marker == "<<<PAGE:1>>>"
        assert segments[1].marker == "<<<PAGE:2>>>"
        assert join_pages(segments) == text

    def test_boilerplate_key_masks_page_numbers(self):
        key_a = boilerplate_line_key("Internal Use | Page 8 of 15")
        key_b = boilerplate_line_key("Internal Use | Page 9 of 15")
        assert key_a == key_b


class TestBoilerplateRemoval:
    def test_removes_repeated_headers(self):
        text = _multi_page_text(
            [
                ("<<<PAGE:1>>>", ["ACME Corp", "Quarterly Report", "Revenue grew."]),
                ("<<<PAGE:2>>>", ["ACME Corp", "Quarterly Report", "Costs declined."]),
                ("<<<PAGE:3>>>", ["ACME Corp", "Quarterly Report", "Margins improved."]),
            ]
        )
        normalizer = CanonicalNormalizer(_settings(minimum_header_frequency=2))
        result = normalizer.normalize(text)
        assert "ACME Corp" not in result
        assert "Quarterly Report" not in result
        assert "Revenue grew." in result
        assert "Margins improved." in result
        assert "<<<PAGE:1>>>" in result
        assert "<<<PAGE:3>>>" in result

    def test_removes_repeated_footers_with_page_numbers(self):
        footer = "Internal Use Only | Classification: Internal | © 2026 | Page {n} of 5"
        text = _multi_page_text(
            [
                ("<<<PAGE:1>>>", ["Body one.", footer.format(n=1)]),
                ("<<<PAGE:2>>>", ["Body two.", footer.format(n=2)]),
                ("<<<PAGE:3>>>", ["Body three.", footer.format(n=3)]),
            ]
        )
        normalizer = CanonicalNormalizer(_settings(minimum_footer_frequency=2))
        result = normalizer.normalize(text)
        assert "Internal Use Only" not in result
        assert "Classification: Internal" not in result
        assert "Body one." in result
        assert "Body three." in result

    def test_no_boilerplate_preserved(self):
        text = _multi_page_text(
            [
                ("<<<PAGE:1>>>", ["Unique intro.", "Section A."]),
                ("<<<PAGE:2>>>", ["Different opener.", "Section B."]),
            ]
        )
        result = CanonicalNormalizer().normalize(text)
        assert "Unique intro." in result
        assert "Different opener." in result

    def test_single_page_skips_frequency_removal(self):
        text = "<<<PAGE:1>>>\nHeader Line\nContent stays."
        segments = split_into_pages(text)
        stats = remove_boilerplate(segments, _settings())
        assert stats.headers_removed == 0
        assert "Header Line" in join_pages(segments)

    def test_false_positive_protection_for_body_lines(self):
        text = _multi_page_text(
            [
                ("<<<PAGE:1>>>", ["Revenue Analysis", "Revenue grew in Q1."]),
                ("<<<PAGE:2>>>", ["Revenue Analysis", "Revenue grew in Q2."]),
                ("<<<PAGE:3>>>", ["Revenue Analysis", "Revenue grew in Q3."]),
            ]
        )
        result = CanonicalNormalizer(_settings(maximum_header_lines=1)).normalize(text)
        assert "Revenue grew in Q1." in result
        assert "Revenue grew in Q3." in result


class TestPageNumberRemoval:
    def test_removes_standalone_page_numbers(self):
        text = _multi_page_text(
            [
                ("<<<PAGE:1>>>", ["Content A", "Page 1 of 10"]),
                ("<<<PAGE:2>>>", ["Content B", "8 / 15"]),
                ("<<<PAGE:3>>>", ["Content C", "Page: 3"]),
            ]
        )
        result = CanonicalNormalizer().normalize(text)
        assert "Page 1 of 10" not in result
        assert "8 / 15" not in result
        assert "Page: 3" not in result
        assert "Content A" in result
        assert "<<<PAGE:2>>>" in result

    def test_page_markers_untouched(self):
        text = "<<<PAGE:42>>>\nImportant content."
        result = CanonicalNormalizer().normalize(text)
        assert "<<<PAGE:42>>>" in result


class TestWhitespaceNormalization:
    def test_collapses_excess_spaces_and_blank_lines(self):
        text = "  hello   world  \n\n\n\nline2"
        result, stats = normalize_whitespace(text)
        assert result == "hello world\n\nline2"
        assert stats.lines_normalized >= 1

    def test_preserves_paragraph_boundaries(self):
        text = "Paragraph one.\n\nParagraph two."
        result, _ = normalize_whitespace(text)
        assert result == "Paragraph one.\n\nParagraph two."

    def test_normalizes_tabs(self):
        text = "col1\tcol2"
        result, _ = normalize_whitespace(text)
        assert result == "col1 col2"


class TestUnicodeCleanup:
    def test_normalizes_smart_quotes_and_dashes(self):
        text = "“Smart” quotes — dash"
        result, _ = normalize_unicode(text)
        assert '"' in result
        assert "—" not in result
        assert "-" in result

    def test_removes_invisible_characters(self):
        text = "hello\u200bworld\ufeff"
        result, stats = normalize_unicode(text)
        assert result == "helloworld"
        assert stats.characters_removed >= 2


class TestOCRNoiseCleanup:
    def test_fixes_hyphenation_across_lines(self):
        text = "enter-\nprise"
        result, stats = clean_ocr_noise(text)
        assert result == "enterprise"
        assert stats.lines_normalized >= 1

    def test_collapses_duplicate_punctuation(self):
        text = "Wait!!! Really???"
        result, _ = clean_ocr_noise(text)
        assert result == "Wait! Really?"

    def test_removes_isolated_garbage_characters(self):
        text = "Valid line\n@@\nAnother valid line"
        result, stats = clean_ocr_noise(text)
        assert "@@" not in result
        assert "Valid line" in result
        assert stats.characters_removed >= 2


class TestCanonicalNormalizer:
    def test_idempotent(self):
        text = _multi_page_text(
            [
                ("<<<PAGE:1>>>", ["ACME Corp", "Body text with  extra   spaces."]),
                ("<<<PAGE:2>>>", ["ACME Corp", "More body text.", "Page 2 of 2"]),
            ]
        )
        normalizer = CanonicalNormalizer()
        once = normalizer.normalize(text)
        twice = normalizer.normalize(once)
        assert once == twice

    def test_disabled_features(self):
        text = "“Smart” — dash\nenter-\nprise"
        settings = _settings(
            enable_boilerplate_removal=False,
            enable_unicode_cleanup=False,
            enable_ocr_cleanup=False,
        )
        result = CanonicalNormalizer(settings).normalize(text)
        assert "“" in result or '"' in result

    def test_large_document_performance(self):
        pages = []
        for i in range(1, 51):
            pages.append(
                (
                    f"<<<PAGE:{i}>>>",
                    [
                        "Enterprise Document Header",
                        f"Content paragraph {i} with meaningful enterprise policy details.",
                        "Internal Use Only | Page {n} of 50".format(n=i),
                    ],
                )
            )
        text = _multi_page_text(pages)
        normalizer = CanonicalNormalizer()
        result, stats = normalizer.normalize_with_stats(text)
        assert "Enterprise Document Header" not in result
        assert "Content paragraph 25" in result
        assert stats.pages_processed == 50
        assert stats.duration_ms >= 0

    def test_mixed_boilerplate_and_content(self):
        text = _multi_page_text(
            [
                ("<<<PAGE:1>>>", ["Doc Title v2.1", "Section 1", "Real content."]),
                ("<<<PAGE:2>>>", ["Doc Title v2.1", "Section 2", "More content."]),
                ("<<<PAGE:3>>>", ["Doc Title v2.1", "Section 3", "Final content."]),
            ]
        )
        result = CanonicalNormalizer().normalize(text)
        assert "Doc Title v2.1" not in result
        assert "Real content." in result
        assert "Final content." in result

    def test_stats_populated(self):
        text = _multi_page_text(
            [
                ("<<<PAGE:1>>>", ["Header", "Body", "Page 1 of 2"]),
                ("<<<PAGE:2>>>", ["Header", "Body 2", "Page 2 of 2"]),
            ]
        )
        _, stats = CanonicalNormalizer().normalize_with_stats(text)
        assert stats.pages_processed == 2
        assert stats.duration_ms >= 0


class TestProcessorIntegration:
    def test_normalize_text_static_helper(self):
        assert DefaultDocumentProcessor.normalize_text("  hello  ") == "hello"

    def test_processor_instance_normalization(self):
        processor = DefaultDocumentProcessor()
        assert processor._normalize("line1\n\n\n\nline2") == "line1\n\nline2"
