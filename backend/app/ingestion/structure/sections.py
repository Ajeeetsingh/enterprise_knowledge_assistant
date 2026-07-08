"""Section hierarchy construction."""

from __future__ import annotations

from app.ingestion.structure.headings import DetectedHeading
from app.ingestion.structure.lists import DetectedList
from app.ingestion.structure.models import (
    BlockMetadata,
    BlockType,
    DocumentBlock,
    HeadingBlock,
    ListStructure,
    ParagraphBlock,
    Section,
    TableStructure,
)
from app.ingestion.structure.paragraphs import DetectedParagraph
from app.ingestion.structure.tables import DetectedTable


def _page_range(values: list[int | None]) -> tuple[int | None, int | None]:
    pages = [page for page in values if page is not None]
    if not pages:
        return None, None
    return min(pages), max(pages)


def build_sections(
    headings: list[DetectedHeading],
    blocks: list[DocumentBlock],
) -> list[Section]:
    """Build nested sections from detected headings and flat blocks."""
    if not headings:
        root = Section(
            section_id="section-1",
            title="Document Body",
            section_number=None,
            level=1,
            blocks=blocks,
        )
        _populate_section_content(root)
        return [root]

    roots: list[Section] = []
    stack: list[Section] = []
    section_by_heading_index: dict[int, Section] = {}

    for heading in headings:
        section = Section(
            section_id=f"section-{heading.line_index}",
            title=heading.text,
            section_number=heading.section_number,
            level=heading.level,
            page_start=heading.page,
            page_end=heading.page,
        )
        section_by_heading_index[heading.line_index] = section

        while stack and stack[-1].level >= heading.level:
            stack.pop()

        if stack:
            stack[-1].subsections.append(section)
        else:
            roots.append(section)
        stack.append(section)

    _assign_blocks_to_sections(blocks, headings, roots, section_by_heading_index)
    for section in _flatten_sections(roots):
        _populate_section_content(section)
    return roots


def _flatten_sections(sections: list[Section]) -> list[Section]:
    flattened: list[Section] = []
    for section in sections:
        flattened.append(section)
        flattened.extend(_flatten_sections(section.subsections))
    return flattened


def _block_line_index(block: DocumentBlock) -> int:
    metadata = _block_metadata(block)
    if metadata is None:
        return 0
    if block.heading is not None:
        return metadata.reading_order
    if block.paragraph is not None:
        return block.paragraph.metadata.reading_order
    if block.table is not None and block.table.metadata is not None:
        return block.table.metadata.reading_order
    if block.list_block is not None and block.list_block.metadata is not None:
        return block.list_block.metadata.reading_order
    return metadata.reading_order


def _assign_blocks_to_sections(
    blocks: list[DocumentBlock],
    headings: list[DetectedHeading],
    roots: list[Section],
    section_by_heading_index: dict[int, Section],
) -> None:
    if not roots:
        return

    heading_positions = sorted(headings, key=lambda item: item.line_index)
    default_section = roots[0]

    for block in blocks:
        if block.heading is not None:
            section = section_by_heading_index.get(block.heading.metadata.reading_order)
            if section is not None:
                section.blocks.append(block)
            continue

        line_index = _line_index_for_block(block)
        active_section = default_section
        for heading in heading_positions:
            if heading.line_index <= line_index:
                active_section = section_by_heading_index[heading.line_index]
            else:
                break
        active_section.blocks.append(block)


def _line_index_for_block(block: DocumentBlock) -> int:
    if block.paragraph is not None:
        return block.paragraph.metadata.reading_order
    if block.table is not None and block.table.metadata is not None:
        return block.table.metadata.reading_order
    if block.list_block is not None and block.list_block.metadata is not None:
        return block.list_block.metadata.reading_order
    return 0


def _populate_section_content(section: Section) -> None:
    section.paragraphs = [
        block.paragraph for block in section.blocks if block.paragraph is not None
    ]
    section.tables = [
        block.table for block in section.blocks if block.table is not None
    ]
    section.lists = [
        block.list_block for block in section.blocks if block.list_block is not None
    ]
    section.headings = [
        block.heading for block in section.blocks if block.heading is not None
    ]

    pages: list[int | None] = []
    for block in section.blocks:
        metadata = _block_metadata(block)
        if metadata is not None:
            pages.extend([metadata.page_start, metadata.page_end])
    page_start, page_end = _page_range(pages)
    if page_start is not None:
        section.page_start = page_start
    if page_end is not None:
        section.page_end = page_end

    for subsection in section.subsections:
        _populate_section_content(subsection)


def _block_metadata(block: DocumentBlock) -> BlockMetadata | None:
    if block.paragraph is not None:
        return block.paragraph.metadata
    if block.heading is not None:
        return block.heading.metadata
    if block.table is not None:
        return block.table.metadata
    if block.list_block is not None:
        return block.list_block.metadata
    return None


def make_document_blocks(
    headings: list[DetectedHeading],
    tables: list[DetectedTable],
    lists: list[DetectedList],
    paragraphs: list[DetectedParagraph],
) -> list[DocumentBlock]:
    """Create flat reading-order blocks from detected structures."""
    events: list[tuple[int, str, object]] = []
    for heading in headings:
        events.append((heading.line_index, "heading", heading))
    for table in tables:
        events.append((table.start_line_index, "table", table))
    for list_block in lists:
        events.append((list_block.start_line_index, "list", list_block))
    for paragraph in paragraphs:
        events.append((paragraph.start_line_index, "paragraph", paragraph))

    events.sort(key=lambda item: (item[0], item[1]))
    blocks: list[DocumentBlock] = []
    for reading_order, (_, kind, payload) in enumerate(events):
        if kind == "heading":
            heading = payload  # type: DetectedHeading
            metadata = BlockMetadata(
                block_type=BlockType.HEADING,
                reading_order=heading.line_index,
                section_title=heading.text,
                section_number=heading.section_number,
                heading_level=heading.level,
                page_start=heading.page,
                page_end=heading.page,
            )
            blocks.append(
                DocumentBlock(
                    block_type=BlockType.HEADING,
                    heading=HeadingBlock(
                        text=heading.text,
                        level=heading.level,
                        section_number=heading.section_number,
                        metadata=metadata,
                    ),
                )
            )
        elif kind == "table":
            table = payload  # type: DetectedTable
            table_id = f"table-{table.start_line_index}"
            metadata = BlockMetadata(
                block_type=BlockType.TABLE,
                reading_order=table.start_line_index,
                table_id=table_id,
                page_start=table.page_start,
                page_end=table.page_end,
            )
            blocks.append(
                DocumentBlock(
                    block_type=BlockType.TABLE,
                    table=TableStructure(
                        table_id=table_id,
                        headers=table.headers,
                        rows=table.rows,
                        page_start=table.page_start,
                        page_end=table.page_end,
                        metadata=metadata,
                    ),
                )
            )
        elif kind == "list":
            list_block = payload  # type: DetectedList
            list_id = f"list-{list_block.start_line_index}"
            metadata = BlockMetadata(
                block_type=BlockType.LIST,
                reading_order=list_block.start_line_index,
                list_id=list_id,
                page_start=list_block.page_start,
                page_end=list_block.page_end,
            )
            blocks.append(
                DocumentBlock(
                    block_type=BlockType.LIST,
                    list_block=ListStructure(
                        list_id=list_id,
                        ordered=list_block.ordered,
                        items=list_block.items,
                        page_start=list_block.page_start,
                        page_end=list_block.page_end,
                        metadata=metadata,
                    ),
                )
            )
        elif kind == "paragraph":
            paragraph = payload  # type: DetectedParagraph
            metadata = BlockMetadata(
                block_type=BlockType.PARAGRAPH,
                reading_order=paragraph.start_line_index,
                page_start=paragraph.page_start,
                page_end=paragraph.page_end,
            )
            blocks.append(
                DocumentBlock(
                    block_type=BlockType.PARAGRAPH,
                    paragraph=ParagraphBlock(text=paragraph.text, metadata=metadata),
                )
            )
    return blocks


def hierarchy_depth(sections: list[Section]) -> int:
    """Return the maximum section nesting depth."""
    if not sections:
        return 0
    return max(_section_depth(section) for section in sections)


def _section_depth(section: Section, current: int = 1) -> int:
    if not section.subsections:
        return current
    return max(_section_depth(child, current + 1) for child in section.subsections)
