"""Internal document structure models for Phase 12.3B."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BlockType(str, Enum):
    """Supported structural block types."""

    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    LIST = "list"


@dataclass(frozen=True)
class BlockMetadata:
    """Internal structural metadata attached to each block."""

    block_type: BlockType
    reading_order: int
    section_title: str | None = None
    section_number: str | None = None
    heading_level: int | None = None
    table_id: str | None = None
    list_id: str | None = None
    list_level: int | None = None
    page_start: int | None = None
    page_end: int | None = None


@dataclass
class ParagraphBlock:
    """A preserved paragraph block."""

    text: str
    metadata: BlockMetadata


@dataclass
class HeadingBlock:
    """A detected heading with hierarchy level."""

    text: str
    level: int
    section_number: str | None
    metadata: BlockMetadata


@dataclass
class TableStructure:
    """Structured table representation without flattening."""

    table_id: str
    headers: list[str]
    rows: list[list[str]]
    page_start: int | None = None
    page_end: int | None = None
    metadata: BlockMetadata | None = None


@dataclass
class ListItem:
    """A list item with optional nesting."""

    text: str
    level: int = 0
    children: list[ListItem] = field(default_factory=list)


@dataclass
class ListStructure:
    """Structured list representation."""

    list_id: str
    ordered: bool
    items: list[ListItem]
    page_start: int | None = None
    page_end: int | None = None
    metadata: BlockMetadata | None = None


@dataclass
class DocumentBlock:
    """Union-like block in flat reading order."""

    block_type: BlockType
    paragraph: ParagraphBlock | None = None
    heading: HeadingBlock | None = None
    table: TableStructure | None = None
    list_block: ListStructure | None = None

    @property
    def text(self) -> str:
        if self.paragraph is not None:
            return self.paragraph.text
        if self.heading is not None:
            return self.heading.text
        if self.table is not None:
            parts = [" | ".join(self.table.headers)]
            parts.extend(" | ".join(row) for row in self.table.rows)
            return "\n".join(parts)
        if self.list_block is not None:
            return _render_list_text(self.list_block.items)
        return ""


@dataclass
class Section:
    """Logical document section with nested subsections."""

    section_id: str
    title: str
    section_number: str | None
    level: int
    page_start: int | None = None
    page_end: int | None = None
    headings: list[HeadingBlock] = field(default_factory=list)
    paragraphs: list[ParagraphBlock] = field(default_factory=list)
    tables: list[TableStructure] = field(default_factory=list)
    lists: list[ListStructure] = field(default_factory=list)
    blocks: list[DocumentBlock] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)


@dataclass
class StructureStats:
    """Structured metrics from a structure extraction run."""

    sections_detected: int = 0
    tables_detected: int = 0
    lists_detected: int = 0
    headings_detected: int = 0
    paragraphs_detected: int = 0
    hierarchy_depth: int = 0
    duration_ms: float = 0.0


@dataclass
class StructuredDocument:
    """Full hierarchical document representation."""

    source: str
    sections: list[Section]
    blocks: list[DocumentBlock]
    stats: StructureStats
    raw_text: str

    @property
    def hierarchy_depth(self) -> int:
        return self.stats.hierarchy_depth


def _render_list_text(items: list[ListItem], level: int = 0) -> str:
    lines: list[str] = []
    for item in items:
        prefix = "  " * level + "- "
        lines.append(f"{prefix}{item.text}")
        if item.children:
            lines.append(_render_list_text(item.children, level + 1))
    return "\n".join(lines)
