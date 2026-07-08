"""Unit tests for Phase 12.3B document structure extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.normalization.page_segments import is_page_marker
from app.ingestion.processor import DefaultDocumentProcessor
from app.ingestion.structure import StructureExtractor
from app.ingestion.structure.config import StructureExtractionSettings
from app.ingestion.structure.headings import detect_headings
from app.ingestion.structure.line_stream import parse_line_stream
from app.ingestion.structure.lists import detect_lists
from app.ingestion.structure.models import BlockType
from app.ingestion.structure.tables import detect_tables
from app.ingestion.structure.validator import validate_structure

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = BACKEND_ROOT.parent / "data"


def _extract(text: str, source: str = "sample.pdf"):
    return StructureExtractor().extract(text, source)


class TestHeadingDetection:
    def test_numbered_headings(self):
        text = """<<<PAGE:1>>>
1. About the Company
Body paragraph one.

1.1 Governance Structure
Nested body paragraph.
"""
        doc = _extract(text)
        headings = [block.heading.text for block in doc.blocks if block.heading]
        assert "1 About the Company" in headings
        assert "1.1 Governance Structure" in headings

    def test_section_and_appendix_headings(self):
        text = """<<<PAGE:1>>>
Section 4 Risk Management
Scope
Definitions
Appendix A Data Retention
"""
        doc = _extract(text)
        headings = [block.heading.text for block in doc.blocks if block.heading]
        assert any("Section 4" in heading for heading in headings)
        assert "Scope" in headings
        assert "Definitions" in headings
        assert any("Appendix A" in heading for heading in headings)

    def test_split_number_title_lines(self):
        text = """<<<PAGE:1>>>
1.
Welcome Message
2.
About GTFS
"""
        doc = _extract(text)
        headings = [block.heading.text for block in doc.blocks if block.heading]
        assert "1 Welcome Message" in headings
        assert "2 About GTFS" in headings

    def test_all_caps_heading(self):
        text = "COMPANY OVERVIEW\nIntro paragraph."
        lines = parse_line_stream(text)
        headings = detect_headings(lines, StructureExtractionSettings())
        assert headings[0].text == "COMPANY OVERVIEW"
        assert headings[0].level == 1


class TestTableDetection:
    def test_gap_separated_table(self):
        text = """<<<PAGE:1>>>
Department    Budget    Owner
Finance       100000    CFO
Technology    250000    CTO
"""
        lines = parse_line_stream(text)
        tables = detect_tables(lines, StructureExtractionSettings())
        assert len(tables) == 1
        assert tables[0].headers == ["Department", "Budget", "Owner"]
        assert tables[0].rows[0] == ["Finance", "100000", "CFO"]
        assert tables[0].confidence >= 0.55

    def test_stacked_row_table(self):
        text = """<<<PAGE:1>>>
Executive
Position
Key Responsibilities
Sarah Mitchell
Chief Executive Officer (CEO)
Overall strategic leadership.
Daniel Carter
Chief Operating Officer (COO)
Operational oversight.
"""
        doc = _extract(text)
        tables = [block.table for block in doc.blocks if block.table]
        assert len(tables) == 1
        assert tables[0].headers == ["Executive", "Position", "Key Responsibilities"]
        assert tables[0].rows[0][0] == "Sarah Mitchell"

    def test_financial_kpi_table_preserved(self):
        text = """<<<PAGE:1>>>
Revenue Stream    FY2026    FY2025    YoY Change
Retail Banking    1000      900       +11.1%
Capital Markets   450       410       +9.8%
Wealth Mgmt       220       205       +7.3%
"""
        lines = parse_line_stream(text)
        tables = detect_tables(lines, StructureExtractionSettings())
        assert len(tables) == 1
        assert tables[0].headers[0] == "Revenue Stream"
        assert tables[0].rows[0][1] == "1000"

    def test_geographic_gap_table_preserved(self):
        text = """<<<PAGE:1>>>
Office            Country     Primary Function
Singapore (HQ)    Singapore   Group headquarters
Dubai Hub         UAE         Regional operations
Mumbai Office     India       South Asia coverage
"""
        lines = parse_line_stream(text)
        tables = detect_tables(lines, StructureExtractionSettings())
        assert len(tables) == 1
        assert tables[0].rows[0][0] == "Singapore (HQ)"

    def test_cover_page_metadata_not_classified_as_table(self):
        text = """<<<PAGE:1>>>
GlobalTrust Financial Services
Trusted. Innovative. Global.
COMPANY OVERVIEW
Corporate Profile & Strategic Overview
Document ID
GTFS-EXEC-001
Version
1.0
Classification
Internal
Owner
Corporate Strategy Office
Approved By
Chief Strategy Officer
"""
        lines = parse_line_stream(text)
        tables = detect_tables(lines, StructureExtractionSettings())
        assert tables == []

    def test_sequential_prose_not_classified_as_stacked_table(self):
        text = """<<<PAGE:9>>>
Banking; Treasury operations; DFSA-regulated entity; Islamic
finance product offerings.
Mumbai (Regional)
India
South Asia market coverage; Retail & Mortgage Services;
Digital Banking innovation lab; RBI-regulated entity; local talent
centre.
London (Regional)
United Kingdom
European & global client coverage; Corporate Banking; Wealth
Management; FCA-regulated entity; cross-border transaction
banking hub.
7. Strategic Priorities for FY2026
The FY2026 Strategic Plan reflects the Board's commitment to accelerating GTFS's digital transformation while
maintaining the financial discipline and risk management standards expected of a regulated financial institution.
"""
        lines = parse_line_stream(text)
        tables = detect_tables(lines, StructureExtractionSettings())
        assert tables == []

    def test_false_positive_prose_becomes_paragraphs(self):
        text = """<<<PAGE:9>>>
Banking; Treasury operations; DFSA-regulated entity; Islamic
finance product offerings.
Mumbai (Regional)
India
South Asia market coverage; Retail & Mortgage Services;
"""
        doc = _extract(text, "prose.pdf")
        assert doc.stats.tables_detected == 0
        paragraphs = [block.paragraph for block in doc.blocks if block.paragraph]
        assert len(paragraphs) >= 1


class TestListDetection:
    def test_bullet_list(self):
        text = """<<<PAGE:1>>>
Policies
- Maintain confidentiality
- Report incidents promptly
"""
        doc = _extract(text)
        lists = [block.list_block for block in doc.blocks if block.list_block]
        assert len(lists) == 1
        assert lists[0].items[0].text == "Maintain confidentiality"

    def test_nested_numbered_list(self):
        text = """<<<PAGE:1>>>
Responsibilities
1. Primary duties
  1. Approve budgets
  2. Review reports
2. Secondary duties
"""
        lines = parse_line_stream(text)
        lists = detect_lists(lines, StructureExtractionSettings())
        assert len(lists) == 1
        assert lists[0].ordered is True
        assert lists[0].items[0].children[0].text == "Approve budgets"


class TestSectionHierarchy:
    def test_nested_sections(self):
        text = """<<<PAGE:1>>>
1. Parent Section
Parent body text.

1.1 Child Section
Child body text.
"""
        doc = _extract(text)
        assert doc.stats.sections_detected >= 2
        assert doc.stats.hierarchy_depth >= 2
        assert doc.sections[0].subsections

    def test_section_metadata(self):
        text = """<<<PAGE:2>>>
2. Leave Policy
Employees are entitled to annual leave.
"""
        doc = _extract(text)
        section = doc.sections[0]
        assert section.title.startswith("2")
        assert section.page_start == 2
        assert section.paragraphs


class TestParagraphPreservation:
    def test_paragraphs_not_merged(self):
        text = """<<<PAGE:1>>>
First paragraph stays separate.

Second paragraph stays separate.
"""
        doc = _extract(text)
        paragraphs = [block.paragraph.text for block in doc.blocks if block.paragraph]
        assert len(paragraphs) == 2
        assert "First paragraph" in paragraphs[0]
        assert "Second paragraph" in paragraphs[1]


class TestValidation:
    def test_reading_order_and_hierarchy(self):
        text = """<<<PAGE:1>>>
1. Scope
This policy defines scope.

- Item one
- Item two
"""
        doc = _extract(text)
        issues = validate_structure(doc)
        assert "Reading order is not monotonic." not in issues
        assert doc.sections

    def test_idempotent_structure_counts(self):
        text = """<<<PAGE:1>>>
1. Definitions
Term one means alpha.
"""
        first = _extract(text)
        second = _extract(text)
        assert first.stats.headings_detected == second.stats.headings_detected
        assert first.stats.paragraphs_detected == second.stats.paragraphs_detected


class TestEnterpriseDocuments:
    @pytest.mark.parametrize(
        "filename",
        [
            "GTFS-EXEC-001_Company_Overview.pdf",
            "GTFS-HR-001_Employee_Handbook.pdf",
            "GTFS-FIN-001_FY2026_Annual_Budget.pdf",
        ],
    )
    def test_real_document_structure(self, filename: str):
        pdf_path = DATA_ROOT / filename
        if not pdf_path.exists():
            pytest.skip(f"Missing corpus file: {filename}")

        from app.ingestion.parsers.pdf import PdfParser

        raw = PdfParser().parse(pdf_path.read_bytes(), filename)
        normalized = DefaultDocumentProcessor.normalize_text(raw)
        doc = _extract(normalized, filename)

        assert doc.stats.headings_detected > 0
        assert doc.stats.sections_detected > 0
        assert doc.stats.paragraphs_detected > 0
        assert doc.blocks
        assert validate_structure(doc) or doc.stats.paragraphs_detected > 0


class TestMixedFormatting:
    def test_handbook_style_document(self):
        text = """<<<PAGE:1>>>
Employee Handbook
1. Welcome Message
Dear colleague,

7. Leave Policy
Annual leave entitlement is 20 days.

Definitions
"Employee" means any permanent staff member.
"""
        doc = _extract(text, "handbook.pdf")
        block_types = {block.block_type for block in doc.blocks}
        assert BlockType.HEADING in block_types
        assert BlockType.PARAGRAPH in block_types
        assert doc.stats.headings_detected >= 3

    def test_financial_report_style_document(self):
        text = """<<<PAGE:1>>>
FY2026 Annual Budget
1. Executive Summary
Revenue forecast remains strong.

Revenue Stream    FY2026    FY2025
Retail Banking    1000      900
Capital Markets   450       410
"""
        doc = _extract(text, "financial.pdf")
        assert doc.stats.tables_detected >= 1
        assert doc.stats.headings_detected >= 1


class TestPageMarkersPreserved:
    def test_page_markers_not_in_blocks(self):
        text = "<<<PAGE:9>>>\n1. Headquarters\nSingapore is HQ."
        doc = _extract(text)
        for block in doc.blocks:
            assert "<<<PAGE:" not in block.text
            if block.heading:
                assert not is_page_marker(block.heading.text)
