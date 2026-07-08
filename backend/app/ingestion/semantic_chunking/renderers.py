"""Content renderers for semantic chunks."""

from __future__ import annotations

from app.ingestion.structure.models import BlockType, DocumentBlock, ListItem, ListStructure, TableStructure


def render_block(block: DocumentBlock) -> str:
    """Render a structured block into embeddable plain text."""
    if block.paragraph is not None:
        return block.paragraph.text.strip()
    if block.heading is not None:
        return block.heading.text.strip()
    if block.table is not None:
        return render_table(block.table)
    if block.list_block is not None:
        return render_list(block.list_block)
    return ""


def render_table(table: TableStructure, rows: list[list[str]] | None = None) -> str:
    """Render a table preserving header, row, and cell relationships."""
    if not table.headers:
        return ""

    selected_rows = table.rows if rows is None else rows
    if len(table.headers) == 1 and not selected_rows:
        return table.headers[0]

    if _looks_like_vertical_field_table(table):
        return _render_vertical_field_table(table, selected_rows)

    lines = [" | ".join(table.headers)]
    for row in selected_rows:
        padded = row + [""] * max(0, len(table.headers) - len(row))
        lines.append(" | ".join(padded[: len(table.headers)]))
    return "\n".join(lines)


def _looks_like_vertical_field_table(table: TableStructure) -> bool:
    if len(table.headers) < 2:
        return False
    if not table.rows:
        return False
    if all(len(row) == len(table.headers) for row in table.rows):
        return True
    return len(table.headers) <= 4


def _render_vertical_field_table(
    table: TableStructure,
    rows: list[list[str]] | None = None,
) -> str:
    """Render row-oriented tables in a field-per-line embeddable format."""
    selected_rows = table.rows if rows is None else rows
    lines: list[str] = []
    for row in selected_rows:
        padded = row + [""] * max(0, len(table.headers) - len(row))
        for header, cell in zip(table.headers, padded):
            header_text = header.strip()
            cell_text = cell.strip()
            if not header_text and not cell_text:
                continue
            if header_text:
                lines.append(f"{header_text}:")
            if cell_text:
                lines.append(cell_text)
            lines.append("")
    return "\n".join(lines).strip()


def render_list(list_block: ListStructure) -> str:
    """Render a complete list with nesting preserved."""
    return _render_list_items(list_block.items, ordered=list_block.ordered)


def _render_list_items(items: list[ListItem], *, ordered: bool, level: int = 0) -> str:
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        indent = "  " * level
        marker = f"{index}." if ordered else "-"
        lines.append(f"{indent}{marker} {item.text.strip()}")
        if item.children:
            lines.append(_render_list_items(item.children, ordered=ordered, level=level + 1))
    return "\n".join(lines)


def render_blocks(blocks: list[DocumentBlock]) -> str:
    """Render multiple blocks into a single chunk body."""
    parts = [render_block(block).strip() for block in blocks]
    return "\n\n".join(part for part in parts if part)


def block_char_count(block: DocumentBlock) -> int:
    return len(render_block(block))


def block_page_range(block: DocumentBlock) -> tuple[int | None, int | None]:
    metadata = _block_metadata(block)
    if metadata is None:
        return None, None
    return metadata.page_start, metadata.page_end


def _block_metadata(block: DocumentBlock):
    if block.paragraph is not None:
        return block.paragraph.metadata
    if block.heading is not None:
        return block.heading.metadata
    if block.table is not None:
        return block.table.metadata
    if block.list_block is not None:
        return block.list_block.metadata
    return None


def count_block_types(blocks: list[DocumentBlock]) -> tuple[int, int, int, bool]:
    paragraphs = sum(1 for block in blocks if block.block_type == BlockType.PARAGRAPH)
    tables = sum(1 for block in blocks if block.block_type == BlockType.TABLE)
    lists = sum(1 for block in blocks if block.block_type == BlockType.LIST)
    has_heading = any(block.block_type == BlockType.HEADING for block in blocks)
    return paragraphs, tables, lists, has_heading
