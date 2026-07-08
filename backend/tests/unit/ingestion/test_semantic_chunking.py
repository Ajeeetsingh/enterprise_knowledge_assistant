"""Unit tests for Phase 12.4 semantic chunk generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.processor import DefaultDocumentProcessor
from app.ingestion.semantic_chunking import SemanticChunkEngine
from app.ingestion.semantic_chunking.ids import stable_chunk_id
from app.ingestion.semantic_chunking.renderers import render_table
from app.ingestion.semantic_chunking.types import ChunkType
from app.ingestion.semantic_chunking.validator import validate_semantic_chunks
from app.ingestion.semantic_chunking.assembler import assemble_semantic_chunks
from app.ingestion.semantic_chunking.config import SemanticChunkingSettings
from app.ingestion.structure import StructureExtractor
from app.ingestion.structure.models import TableStructure
from app.ingestion.structure.models import BlockMetadata, BlockType


BACKEND_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = BACKEND_ROOT.parent / "data"


def _chunk(text: str, source: str = "sample.pdf"):
    structured = StructureExtractor().extract(text, source)
    return SemanticChunkEngine().chunk_document(structured, source=source, category="general")


class TestTableRendering:
    def test_vertical_field_table_rendering(self):
        table = TableStructure(
            table_id="table-1",
            headers=["Office", "Country", "Primary Function"],
            rows=[
                ["Singapore (HQ)", "Singapore", "Group headquarters"],
                ["Dubai Hub", "UAE", "Regional operations"],
            ],
        )
        rendered = render_table(table)
        assert "Office:" in rendered
        assert "Singapore (HQ)" in rendered
        assert "Primary Function:" in rendered
        assert "Group headquarters" in rendered


class TestSemanticChunkAssembly:
    def test_heading_stays_with_first_paragraph(self):
        text = """<<<PAGE:1>>>
1. Scope
This policy defines the enterprise scope for all employees.
Another paragraph in the same section with more detail.
"""
        chunks = _chunk(text)
        assert chunks
        first = chunks[0].content
        assert "Scope" in first
        assert "enterprise scope" in first

    def test_table_kept_whole(self):
        text = """<<<PAGE:1>>>
Executive Leadership
Executive
Position
Responsibilities
Sarah Mitchell
Chief Executive Officer
Strategic leadership
Daniel Carter
Chief Operating Officer
Operational leadership
"""
        chunks = _chunk(text)
        table_chunks = [c for c in chunks if c.metadata and c.metadata.contains_table]
        assert table_chunks
        assert "Executive:" in table_chunks[0].content or "Sarah Mitchell" in table_chunks[0].content

    def test_list_kept_together(self):
        text = """<<<PAGE:1>>>
Policies
- Maintain confidentiality
- Report incidents promptly
- Complete annual training
"""
        chunks = _chunk(text)
        list_chunks = [c for c in chunks if c.metadata and c.metadata.contains_list]
        assert list_chunks
        assert "Maintain confidentiality" in list_chunks[0].content
        assert "annual training" in list_chunks[0].content

    def test_nested_list_preserved(self):
        text = """<<<PAGE:1>>>
Responsibilities
- Primary duties
  - Approve budgets
  - Review reports
"""
        chunks = _chunk(text)
        assert any("Approve budgets" in chunk.content for chunk in chunks)

    def test_small_section_kept_together(self):
        text = """<<<PAGE:1>>>
2. Vision
We innovate responsibly.
"""
        chunks = _chunk(text)
        assert len(chunks) == 1
        assert "Vision" in chunks[0].content
        assert "innovate" in chunks[0].content


class TestChunkMetadata:
    def test_metadata_fields_populated(self):
        text = """<<<PAGE:2>>>
3. Leave Policy
Employees receive annual leave.
"""
        chunks = _chunk(text)
        metadata = chunks[0].metadata
        assert metadata is not None
        assert metadata.chunk_type in {ChunkType.MIXED, ChunkType.SUBSECTION, ChunkType.PARAGRAPH}
        assert metadata.page_start == 2
        assert metadata.contains_heading is True
        assert metadata.paragraph_count >= 1
        assert metadata.character_count > 0
        assert metadata.hierarchy_path

    def test_chunk_type_distribution(self):
        text = """<<<PAGE:1>>>
Policies
Only paragraph content here without headings beyond the keyword.
"""
        chunks = _chunk(text)
        assert chunks[0].metadata is not None


class TestStableChunkIds:
    def test_ids_use_block_keys_not_sequence(self):
        text = """<<<PAGE:1>>>
1. Alpha
Alpha paragraph.

2. Beta
Beta paragraph.
"""
        first = _chunk(text, "stable.pdf")
        second = _chunk(text.replace("Beta", "Gamma"), "stable.pdf")
        first_ids = {chunk.chunk_id for chunk in first}
        second_ids = {chunk.chunk_id for chunk in second}
        assert first_ids & second_ids

    def test_stable_chunk_id_format(self):
        structured = StructureExtractor().extract(
            "<<<PAGE:1>>>\n1. Alpha\nAlpha body.",
            "doc.pdf",
        )
        assembled = assemble_semantic_chunks(
            structured,
            "general",
            SemanticChunkingSettings(),
        )
        assert assembled
        assert assembled[0].blocks


class TestValidation:
    def test_no_duplicate_block_assignment(self):
        text = """<<<PAGE:1>>>
1. Definitions
Term one means alpha.

2. Scope
Scope paragraph one.
"""
        structured = StructureExtractor().extract(text, "doc.pdf")
        engine = SemanticChunkEngine()
        chunks = engine.chunk_document(structured, source="doc.pdf", category="general")
        assembled = assemble_semantic_chunks(structured, "general", SemanticChunkingSettings())
        for chunk in assembled:
            chunk.chunk_id = stable_chunk_id("doc.pdf", chunk.blocks)
        issues = validate_semantic_chunks(structured, assembled)
        assert "Duplicate block assignment detected." not in issues
        assert chunks

    def test_reading_order_preserved(self):
        text = """<<<PAGE:1>>>
1. One
Paragraph one.

2. Two
Paragraph two.
"""
        chunks = _chunk(text)
        orders = [chunk.metadata.reading_order for chunk in chunks if chunk.metadata]
        assert orders == sorted(orders)


class TestMixedContent:
    def test_handbook_style_chunk(self):
        text = """<<<PAGE:1>>>
1. Welcome Message
Dear colleague, welcome to GTFS.

7. Leave Policy
- 20 days annual leave
- 12 days sick leave
"""
        chunks = _chunk(text, "handbook.pdf")
        assert any("Welcome" in c.content for c in chunks)
        assert any("annual leave" in c.content for c in chunks)

    def test_financial_report_table_chunk(self):
        text = """<<<PAGE:1>>>
4. Revenue Forecast
Revenue Stream    FY2026    FY2025
Retail Banking    1000      900
Capital Markets   450       410
"""
        chunks = _chunk(text, "financial.pdf")
        assert any(
            c.metadata and c.metadata.contains_table
            for c in chunks
        )


class TestHugeAppendixSplit:
    def test_large_section_splits_at_block_boundaries(self):
        paragraphs = "\n\n".join(
            f"Paragraph {i} with enterprise policy details and operational guidance."
            for i in range(1, 30)
        )
        text = f"<<<PAGE:1>>>\nAppendix A\n{paragraphs}"
        settings = SemanticChunkingSettings(
            max_preferred_chunk_size=1200,
            soft_max_chunk_size=1500,
            absolute_max_chunk_size=1800,
            max_paragraph_merge=2,
        )
        structured = StructureExtractor().extract(text, "appendix.pdf")
        chunks = SemanticChunkEngine(settings=settings).chunk_document(
            structured,
            source="appendix.pdf",
            category="general",
        )
        assert len(chunks) > 1
        sizes = [len(chunk.content) for chunk in chunks]
        assert max(sizes) <= 1800
        assert all("Paragraph" in chunk.content for chunk in chunks[:3])


class TestRefinedChunkSizing:
    def test_long_section_produces_multiple_retrieval_units(self):
        paragraphs = []
        for i in range(1, 12):
            paragraphs.append(f"<<<PAGE:{i}>>>\n{i} Section Topic")
            paragraphs.append(
                f"Paragraph {i} discusses enterprise policy controls, governance, "
                f"and operational requirements in detail for staff."
            )
        text = "\n\n".join(paragraphs)
        structured = StructureExtractor().extract(text, "long.pdf")
        chunks, stats = SemanticChunkEngine().chunk_document_with_stats(
            structured,
            source="long.pdf",
            category="general",
        )
        assert stats.chunks_created >= 8
        assert stats.average_chunk_size <= 1500
        assert stats.median_chunk_size <= 1400
        assert stats.largest_chunk <= 1800
        assert chunks


class TestTableSplitting:
    def test_oversized_table_splits_at_row_boundaries(self):
        rows = [
            [f"Field {i}", f"Value {i} " + ("detail " * 40)]
            for i in range(1, 25)
        ]
        table = TableStructure(
            table_id="table-large",
            headers=["Metric", "Details"],
            rows=rows,
        )
        from app.ingestion.structure.models import DocumentBlock

        block = DocumentBlock(block_type=BlockType.TABLE, table=table)
        settings = SemanticChunkingSettings(
            max_preferred_chunk_size=1200,
            absolute_max_chunk_size=1800,
        )
        from app.ingestion.semantic_chunking.assembler import _split_table_group

        groups = _split_table_group(block, settings)
        assert len(groups) > 1
        sizes = [len(render_table(group[0].table)) for group in groups if group[0].table]
        assert max(sizes) <= 1800
        assert all("Metric" in render_table(group[0].table) for group in groups if group[0].table)

    def test_table_isolated_from_paragraphs(self):
        text = """<<<PAGE:1>>>
Revenue Summary
Retail banking grew steadily across all regions this year.

Metric
FY2026
FY2025
Retail Banking
1000
900
Capital Markets
450
410
"""
        chunks = _chunk(text, "split.pdf")
        mixed_with_table_and_para = [
            chunk
            for chunk in chunks
            if chunk.metadata
            and chunk.metadata.contains_table
            and chunk.metadata.paragraph_count > 0
        ]
        assert not mixed_with_table_and_para


class TestEnterpriseDocument:
    @pytest.mark.parametrize(
        "filename",
        ["GTFS-EXEC-001_Company_Overview.pdf"],
    )
    def test_exec_overview_semantic_chunks(self, filename: str):
        pdf_path = DATA_ROOT / filename
        if not pdf_path.exists():
            pytest.skip(f"Missing corpus file: {filename}")
        from app.ingestion.parsers.pdf import PdfParser

        raw = PdfParser().parse(pdf_path.read_bytes(), filename)
        normalized = DefaultDocumentProcessor.normalize_text(raw)
        structured = StructureExtractor().extract(normalized, filename)
        chunks, stats = SemanticChunkEngine().chunk_document_with_stats(
            structured,
            source=filename,
            category="overview",
        )
        assert stats.chunks_created >= 35
        assert stats.average_chunk_size <= 1200
        assert stats.median_chunk_size <= 1200
        assert stats.largest_chunk <= 4000
        assert chunks[0].metadata is not None
        assert "<<<PAGE:" not in chunks[0].content
