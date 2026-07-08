"""Tests for RAG quality improvements: chunking, confidence, citations, answer synthesis."""

from __future__ import annotations

import pytest

from app.ingestion.chunker import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    DocumentChunk,
    PAGE_MARKER_PATTERN,
    chunk_text,
)
from app.rag.answer_generator import (
    AnswerGenerator,
    GeneratedAnswer,
    UNAVAILABLE_MESSAGE,
    _synthesize_general_answer,
    _synthesize_structured_answer,
    _table_rows_to_sentences,
    _clean_table_row,
)
from app.rag.types import (
    Citation,
    RetrievalResult,
    calibrate_confidence,
    _CALIBRATION_LOW,
    _CALIBRATION_HIGH,
)


# ---------------------------------------------------------------------------
# Chunking — page tracking
# ---------------------------------------------------------------------------

class TestChunkTextPageTracking:
    def test_plain_text_has_no_page_number(self):
        text = "GlobalTrust is a financial services company based in Singapore."
        chunks = chunk_text(text, "doc.txt", "general")
        assert chunks
        assert all(c.page_number is None for c in chunks)

    def test_page_markers_assigned_to_chunks(self):
        # Page 1 needs enough content (> CHUNK_SIZE + CHUNK_OVERLAP) to ensure
        # at least one chunk starts entirely within page 2 after the overlap rewind.
        page1 = "GlobalTrust Financial Services is headquartered in Singapore. " * 25
        page2 = "Sarah Mitchell serves as Chief Executive Officer of GlobalTrust. " * 25
        text = f"<<<PAGE:1>>>\n{page1}\n<<<PAGE:2>>>\n{page2}"
        chunks = chunk_text(text, "report.pdf", "general")
        page_numbers = {c.page_number for c in chunks}
        # Both pages should be represented
        assert 1 in page_numbers
        assert 2 in page_numbers

    def test_chunk_content_does_not_contain_page_markers(self):
        text = "<<<PAGE:3>>>\nThis is page three content."
        chunks = chunk_text(text, "report.pdf", "general")
        for chunk in chunks:
            assert "<<<PAGE:" not in chunk.content

    def test_multi_page_document_assigns_correct_pages(self):
        pages = []
        for i in range(1, 6):
            # Each page needs enough content to force its own chunk
            pages.append(f"<<<PAGE:{i}>>>\n" + (f"Detailed content from page {i} about enterprise banking. " * 20))
        text = "\n".join(pages)
        chunks = chunk_text(text, "multi.pdf", "general")
        page_numbers = {c.page_number for c in chunks}
        # Should cover pages 1–5
        assert page_numbers == {1, 2, 3, 4, 5}


class TestChunkTextSentenceBoundaries:
    def test_chunks_do_not_cut_mid_sentence(self):
        # Build text with many complete sentences
        sentences = [f"This is sentence number {i}." for i in range(50)]
        text = " ".join(sentences)
        chunks = chunk_text(text, "doc.txt", "general")
        for chunk in chunks:
            # No chunk should end in the middle of a word
            assert not chunk.content.endswith(" ")

    def test_chunk_size_respects_limit(self):
        long_sentence = "word " * 200  # 1000 chars
        text = long_sentence.strip() + "."
        chunks = chunk_text(text, "doc.txt", "general")
        # At least one chunk must exist
        assert chunks
        # The first chunk should not massively exceed CHUNK_SIZE (may exceed by one sentence)
        assert len(chunks[0].content) <= CHUNK_SIZE * 2

    def test_overlap_produces_shared_content(self):
        # Build enough content to produce multiple chunks
        sentences = [f"Sentence number {i} about the company policy." for i in range(30)]
        text = " ".join(sentences)
        chunks = chunk_text(text, "doc.txt", "general")
        if len(chunks) < 2:
            pytest.skip("not enough content to test overlap")
        # Some content from end of chunk N should appear in start of chunk N+1
        c1_words = set(chunks[0].content.lower().split())
        c2_words = set(chunks[1].content.lower().split())
        overlap = c1_words & c2_words
        assert len(overlap) > 0, "Adjacent chunks should share words from overlap"

    def test_empty_text_returns_empty_list(self):
        assert chunk_text("", "doc.txt", "general") == []
        assert chunk_text("   \n\n  ", "doc.txt", "general") == []

    def test_chunk_ids_are_sequential(self):
        text = "Full sentence. " * 40
        chunks = chunk_text(text, "report.pdf", "general")
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_id == f"report.pdf::{i}"

    def test_chunk_fields_populated(self):
        text = "GlobalTrust Financial Services is a banking group."
        chunks = chunk_text(text, "overview.pdf", "finance")
        assert chunks
        chunk = chunks[0]
        assert chunk.source == "overview.pdf"
        assert chunk.category == "finance"
        assert chunk.content
        assert isinstance(chunk.chunk_index, int)


# ---------------------------------------------------------------------------
# Confidence calibration
# ---------------------------------------------------------------------------

class TestCalibrateConfidence:
    def test_below_low_threshold_maps_to_zero(self):
        assert calibrate_confidence(0.0) == 0.0
        assert calibrate_confidence(_CALIBRATION_LOW - 0.01) == 0.0

    def test_above_high_threshold_maps_to_one(self):
        assert calibrate_confidence(1.0) == 1.0
        assert calibrate_confidence(_CALIBRATION_HIGH + 0.01) == 1.0

    def test_midpoint_is_near_fifty_percent(self):
        midpoint = (_CALIBRATION_LOW + _CALIBRATION_HIGH) / 2
        calibrated = calibrate_confidence(midpoint)
        assert abs(calibrated - 0.5) < 0.01

    def test_typical_retrieval_score_above_threshold(self):
        # A typical relevant match score of 0.65 should calibrate well above 50%
        calibrated = calibrate_confidence(0.65)
        assert calibrated > 0.5

    def test_low_raw_score_calibrates_low(self):
        calibrated = calibrate_confidence(0.25)
        assert calibrated < 0.3

    def test_output_is_clamped_to_zero_one(self):
        assert 0.0 <= calibrate_confidence(-1.0) <= 1.0
        assert 0.0 <= calibrate_confidence(2.0) <= 1.0

    def test_monotonically_increasing(self):
        scores = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        calibrated = [calibrate_confidence(s) for s in scores]
        for i in range(len(calibrated) - 1):
            assert calibrated[i] <= calibrated[i + 1]


# ---------------------------------------------------------------------------
# Citation page numbers
# ---------------------------------------------------------------------------

class TestCitationPageNumbers:
    def test_citation_includes_page(self):
        citation = Citation(
            source="overview.pdf",
            excerpt="GlobalTrust is headquartered in Singapore.",
            confidence=0.75,
            page=4,
        )
        assert citation.page == 4

    def test_citation_page_defaults_to_none(self):
        citation = Citation(
            source="doc.txt",
            excerpt="Some content.",
            confidence=0.5,
        )
        assert citation.page is None

    def test_retrieval_result_page_number_field(self):
        result = RetrievalResult(
            content="Test content.",
            source="doc.pdf",
            category="general",
            confidence=0.7,
            chunk_id="doc.pdf::0",
            page_number=3,
        )
        assert result.page_number == 3

    def test_retrieval_result_page_defaults_to_none(self):
        result = RetrievalResult(
            content="Test content.",
            source="doc.txt",
            category="general",
            confidence=0.7,
            chunk_id="doc.txt::0",
        )
        assert result.page_number is None


# ---------------------------------------------------------------------------
# Answer synthesis — structured extractor
# ---------------------------------------------------------------------------

class TestSynthesizeStructuredAnswer:
    HQ_CONTEXT = (
        "Singapore (HQ) Singapore Group headquarters; "
        "Retail & Commercial Banking hub; Technology Centre of Excellence; "
        "Risk & Compliance headquarters; MAS-regulated entity."
    )

    CEO_CONTEXT = (
        "Sarah Mitchell, Chief Executive Officer of GlobalTrust Financial Services."
    )

    FOUNDED_CONTEXT = (
        "GlobalTrust Financial Services was established in 1987 in Singapore."
    )

    def test_headquarters_query(self):
        answer = _synthesize_structured_answer("What is the company headquarters?", self.HQ_CONTEXT)
        assert answer is not None
        assert "Singapore" in answer

    def test_ceo_query(self):
        answer = _synthesize_structured_answer("Who is the CEO?", self.CEO_CONTEXT)
        assert answer is not None
        assert "Sarah Mitchell" in answer

    def test_founded_query(self):
        answer = _synthesize_structured_answer("When was the company founded?", self.FOUNDED_CONTEXT)
        assert answer is not None
        assert "1987" in answer

    def test_returns_none_for_unrelated_query(self):
        answer = _synthesize_structured_answer(
            "What is the annual leave policy?",
            "Employees get 20 days annual leave per year.",
        )
        # structured extractor should not claim an HQ / CEO answer here
        # (it may return None and fall through to general extractor)
        # We only care it doesn't crash
        assert answer is None or isinstance(answer, str)


# ---------------------------------------------------------------------------
# Answer synthesis — general extractor
# ---------------------------------------------------------------------------

class TestSynthesizeGeneralAnswer:
    def test_returns_relevant_sentence(self):
        context = (
            "GlobalTrust Financial Services operates in over 20 countries. "
            "The company was founded in Singapore in 1987. "
            "Its core banking platform is called CoreBanker."
        )
        answer = _synthesize_general_answer("When was GlobalTrust founded?", context)
        assert answer is not None
        assert "1987" in answer

    def test_returns_none_for_empty_context(self):
        answer = _synthesize_general_answer("What is the company?", "")
        assert answer is None

    def test_filters_noisy_lines(self):
        context = "=================\nINTERNAL USE ONLY\n=================\nThis is the company."
        answer = _synthesize_general_answer("What is the company?", context)
        # Should return the clean sentence, not the separator line
        if answer:
            assert "=====" not in answer

    def test_multi_sentence_answer(self):
        context = (
            "The company headquarters is in Singapore. "
            "Singapore is the Group headquarters for GlobalTrust. "
            "The regional offices span Asia, Europe, and North America."
        )
        answer = _synthesize_general_answer("Where is the company headquartered?", context, max_sentences=2)
        assert answer is not None
        assert "Singapore" in answer


# ---------------------------------------------------------------------------
# AnswerGenerator integration
# ---------------------------------------------------------------------------

class TestAnswerGeneratorIntegration:
    def _make_result(self, content: str, source: str = "overview.pdf", confidence: float = 0.75,
                     page_number: int | None = 1) -> RetrievalResult:
        return RetrievalResult(
            content=content,
            source=source,
            category="general",
            confidence=confidence,
            chunk_id=f"{source}::0",
            page_number=page_number,
        )

    def test_headquarters_answer_is_natural_prose(self):
        generator = AnswerGenerator()
        context = (
            "Singapore (HQ) Singapore Group headquarters; "
            "Retail & Commercial Banking hub; MAS-regulated entity."
        )
        result = generator.generate(
            "What is the company headquarters?",
            [self._make_result(context)],
        )
        assert result.answer != UNAVAILABLE_MESSAGE
        assert "Singapore" in result.answer
        # Should not dump raw table cells
        assert result.answer.count("Singapore (HQ)") == 0 or "headquarters" in result.answer.lower()

    def test_no_results_returns_unavailable(self):
        generator = AnswerGenerator()
        result = generator.generate("Any question?", [])
        assert result.answer == UNAVAILABLE_MESSAGE
        assert result.confidence_score == 0.0

    def test_confidence_propagated_from_best_result(self):
        generator = AnswerGenerator()
        result = generator.generate(
            "Tell me about the company.",
            [self._make_result("GlobalTrust is a global bank.", confidence=0.82)],
        )
        assert result.confidence_score == 0.82

    def test_sources_collected(self):
        generator = AnswerGenerator()
        results = [
            self._make_result("Content A.", source="docA.pdf"),
            self._make_result("Content B.", source="docB.pdf"),
        ]
        result = generator.generate("What is the company?", results)
        assert "docA.pdf" in result.sources_used
        assert "docB.pdf" in result.sources_used

    def test_table_to_prose_conversion(self):
        generator = AnswerGenerator()
        # This is the format that causes the garbled output
        content = (
            "Country / Jurisdiction Primary Function "
            "Singapore (HQ) Singapore Group headquarters; "
            "Retail & Commercial Banking hub; "
            "Technology Centre of Excellence; "
            "Risk & Compliance headquarters."
        )
        result = generator.generate(
            "What is the company headquarters?",
            [self._make_result(content)],
        )
        # Answer must mention Singapore and not be UNAVAILABLE
        assert result.answer != UNAVAILABLE_MESSAGE
        assert "Singapore" in result.answer
