"""Semantic chunk assembly from structured document blocks."""

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.semantic_chunking.config import SemanticChunkingSettings
from app.ingestion.semantic_chunking.overlap import apply_semantic_overlap
from app.ingestion.semantic_chunking.renderers import (
    block_char_count,
    block_page_range,
    count_block_types,
    render_blocks,
    render_table,
)
from app.ingestion.semantic_chunking.types import ChunkMetadata, ChunkType
from app.ingestion.semantic_chunking.ids import block_key
from app.ingestion.structure.models import (
    BlockType,
    DocumentBlock,
    ListItem,
    ListStructure,
    Section,
    StructuredDocument,
    TableStructure,
)


@dataclass(frozen=True)
class BlockContext:
    section_title: str | None
    section_number: str | None
    heading_level: int | None
    hierarchy_path: tuple[str, ...]


@dataclass
class AssembledChunk:
    """Intermediate semantic chunk before conversion to DocumentChunk."""

    chunk_id: str
    content: str
    metadata: ChunkMetadata
    page_number: int | None
    blocks: list[DocumentBlock]


def assemble_semantic_chunks(
    document: StructuredDocument,
    category: str,
    settings: SemanticChunkingSettings,
) -> list[AssembledChunk]:
    """Assemble semantic retrieval units from structured blocks in reading order."""
    _ = category
    if not document.blocks:
        return []

    document_title = _infer_document_title(document)
    context_map = _build_block_context_map(document.sections)
    groups = _expand_groups(_group_blocks(document.blocks, settings), settings)
    assembled: list[AssembledChunk] = []
    section_headings: dict[str | None, str | None] = {}

    for order, group in enumerate(groups):
        context = _resolve_group_context(group, context_map)
        section_key = context.section_title
        group_heading = _group_heading_text(group)
        if group_heading:
            section_headings[section_key] = group_heading

        content = render_blocks(group)
        paragraphs, tables, lists, has_heading = count_block_types(group)
        chunk_type = _resolve_chunk_type(
            group,
            has_heading=has_heading,
            hierarchy_path=context.hierarchy_path,
        )
        page_start, page_end = _group_page_range(group)
        metadata = ChunkMetadata(
            chunk_type=chunk_type,
            section_title=context.section_title,
            section_number=context.section_number,
            heading_level=context.heading_level,
            document_title=document_title,
            page_start=page_start,
            page_end=page_end,
            reading_order=order,
            contains_table=tables > 0,
            contains_list=lists > 0,
            contains_heading=has_heading,
            paragraph_count=paragraphs,
            table_count=tables,
            list_count=lists,
            word_count=len(content.split()),
            character_count=len(content),
            hierarchy_path=context.hierarchy_path,
            block_keys=tuple(block_key(block) for block in group),
        )
        chunk = AssembledChunk(
            chunk_id="pending",
            content=content,
            metadata=metadata,
            page_number=page_start,
            blocks=group,
        )
        overlap_heading = None if has_heading else section_headings.get(section_key)
        chunk.content = apply_semantic_overlap(
            chunk.content,
            section_title=context.section_title,
            hierarchy_path=context.hierarchy_path,
            settings=settings,
            is_first_chunk_in_section=_is_first_chunk_for_section(group, groups, order, context_map),
            context_heading=overlap_heading,
        )
        chunk.metadata = ChunkMetadata(
            **{
                **chunk.metadata.__dict__,
                "character_count": len(chunk.content),
                "word_count": len(chunk.content.split()),
            }
        )
        assembled.append(chunk)
    return assembled


def _group_blocks(
    blocks: list[DocumentBlock],
    settings: SemanticChunkingSettings,
) -> list[list[DocumentBlock]]:
    """Adaptively group blocks into retrieval-sized semantic units."""
    groups: list[list[DocumentBlock]] = []
    current: list[DocumentBlock] = []
    current_size = 0
    awaiting_heading_body = False

    def flush() -> None:
        nonlocal current, current_size, awaiting_heading_body
        if current:
            groups.append(current)
        current = []
        current_size = 0
        awaiting_heading_body = False

    for block in blocks:
        block_size = block_char_count(block)

        if block.block_type == BlockType.HEADING:
            # Always flush the previous group. Overwriting while
            # awaiting_heading_body discarded heading-only sections (e.g. when
            # a prior table swallowed their body text).
            if current:
                flush()
            current = [block]
            current_size = block_size
            awaiting_heading_body = True
            continue

        if awaiting_heading_body:
            if (
                block.block_type == BlockType.TABLE
                and current_size + block_size > settings.max_preferred_chunk_size
            ):
                flush()
                groups.append([block])
                continue
            current.append(block)
            current_size += block_size
            awaiting_heading_body = False
            continue

        if current and _should_close_before_add(current, current_size, block, settings):
            flush()

        if (
            not current
            and block_size > settings.absolute_max_chunk_size
            and block.block_type in {BlockType.TABLE, BlockType.LIST, BlockType.PARAGRAPH}
        ):
            groups.append([block])
            continue

        if not current:
            current = [block]
            current_size = block_size
        else:
            current.append(block)
            current_size += block_size

    if current:
        groups.append(current)
    return groups


def _should_close_before_add(
    current: list[DocumentBlock],
    current_size: int,
    next_block: DocumentBlock,
    settings: SemanticChunkingSettings,
) -> bool:
    """Return True when the current chunk should close before adding *next_block*."""
    if _only_heading(current):
        return False

    next_size = block_char_count(next_block)
    combined = current_size + next_size + 2

    if next_block.block_type == BlockType.HEADING:
        return True

    if next_block.block_type == BlockType.TABLE and current_size > 0:
        return True

    if (
        next_block.block_type == BlockType.LIST
        and current_size > 0
        and _paragraph_count(current) > 0
    ):
        return True

    if combined <= settings.max_preferred_chunk_size:
        if (
            next_block.block_type == BlockType.PARAGRAPH
            and _paragraph_count(current) >= settings.max_paragraph_merge
        ):
            return True
        return False

    if combined <= settings.soft_max_chunk_size:
        if next_block.block_type in {BlockType.TABLE, BlockType.LIST}:
            return True
        if (
            next_block.block_type == BlockType.PARAGRAPH
            and _paragraph_count(current) >= settings.max_paragraph_merge
        ):
            return True
        return current_size >= settings.min_chunk_size

    if combined <= settings.absolute_max_chunk_size:
        if next_block.block_type in {BlockType.TABLE, BlockType.LIST}:
            return True
        return current_size >= settings.min_chunk_size

    return True


def _paragraph_count(blocks: list[DocumentBlock]) -> int:
    return sum(1 for block in blocks if block.block_type == BlockType.PARAGRAPH)


def _expand_groups(
    groups: list[list[DocumentBlock]],
    settings: SemanticChunkingSettings,
) -> list[list[DocumentBlock]]:
    """Split oversized atomic blocks at semantic boundaries into retrieval-sized units."""
    expanded: list[list[DocumentBlock]] = []
    for group in groups:
        if len(group) == 1:
            block = group[0]
            if block.table is not None:
                expanded.extend(_split_table_group(block, settings))
                continue
            if block.list_block is not None:
                expanded.extend(_split_list_group(block, settings))
                continue
        expanded.extend(_split_oversized_mixed_group(group, settings))
    return expanded


def _split_oversized_mixed_group(
    group: list[DocumentBlock],
    settings: SemanticChunkingSettings,
) -> list[list[DocumentBlock]]:
    """Break apart mixed groups that exceed absolute max after table/list isolation."""
    if len(group) <= 1:
        return [group]

    size = sum(block_char_count(block) for block in group) + max(0, len(group) - 1) * 2
    if size <= settings.absolute_max_chunk_size:
        return [group]

    subgroups: list[list[DocumentBlock]] = []
    current: list[DocumentBlock] = []
    current_size = 0

    def flush() -> None:
        nonlocal current, current_size
        if current:
            subgroups.append(current)
        current = []
        current_size = 0

    for block in group:
        block_size = block_char_count(block)
        if block.table is not None and block_size > settings.absolute_max_chunk_size:
            flush()
            subgroups.extend(_split_table_group(block, settings))
            continue
        if block.list_block is not None and block_size > settings.absolute_max_chunk_size:
            flush()
            subgroups.extend(_split_list_group(block, settings))
            continue
        if current and current_size + block_size + 2 > settings.max_preferred_chunk_size:
            flush()
        current.append(block)
        current_size += block_size

    if current:
        subgroups.append(current)
    return subgroups if subgroups else [group]


def _split_table_group(
    block: DocumentBlock,
    settings: SemanticChunkingSettings,
) -> list[list[DocumentBlock]]:
    table = block.table
    if table is None or not table.rows:
        return [[block]]

    full_size = block_char_count(block)
    if full_size <= settings.absolute_max_chunk_size:
        return [[block]]

    batches: list[list[list[str]]] = []
    current_rows: list[list[str]] = []
    current_size = len(render_table(table, rows=[])) or len(" | ".join(table.headers))

    for row in table.rows:
        row_only = TableStructure(
            table_id=table.table_id,
            headers=table.headers,
            rows=[row],
            page_start=table.page_start,
            page_end=table.page_end,
            metadata=table.metadata,
        )
        row_block = DocumentBlock(block_type=BlockType.TABLE, table=row_only)
        row_size = block_char_count(row_block) + 2
        if current_rows and current_size + row_size > settings.max_preferred_chunk_size:
            batches.append(current_rows)
            current_rows = []
            current_size = len(render_table(table, rows=[])) or len(" | ".join(table.headers))
        current_rows.append(row)
        current_size += row_size

    if current_rows:
        batches.append(current_rows)

    groups: list[list[DocumentBlock]] = []
    for index, rows in enumerate(batches):
        split_table = TableStructure(
            table_id=f"{table.table_id}::rows-{index}",
            headers=table.headers,
            rows=rows,
            page_start=table.page_start,
            page_end=table.page_end,
            metadata=table.metadata,
        )
        groups.append([DocumentBlock(block_type=BlockType.TABLE, table=split_table)])
    return groups


def _split_list_group(
    block: DocumentBlock,
    settings: SemanticChunkingSettings,
) -> list[list[DocumentBlock]]:
    list_block = block.list_block
    if list_block is None or not list_block.items:
        return [[block]]

    full_size = block_char_count(block)
    if full_size <= settings.absolute_max_chunk_size:
        return [[block]]

    batches: list[list[ListItem]] = []
    current_items: list[ListItem] = []
    current_size = 0

    for item in list_block.items:
        item_only = ListStructure(
            list_id=list_block.list_id,
            ordered=list_block.ordered,
            items=[item],
            page_start=list_block.page_start,
            page_end=list_block.page_end,
            metadata=list_block.metadata,
        )
        item_block = DocumentBlock(block_type=BlockType.LIST, list_block=item_only)
        item_size = block_char_count(item_block) + 2
        if current_items and current_size + item_size > settings.max_preferred_chunk_size:
            batches.append(current_items)
            current_items = []
            current_size = 0
        current_items.append(item)
        current_size += item_size

    if current_items:
        batches.append(current_items)

    groups: list[list[DocumentBlock]] = []
    for index, items in enumerate(batches):
        split_list = ListStructure(
            list_id=f"{list_block.list_id}::items-{index}",
            ordered=list_block.ordered,
            items=items,
            page_start=list_block.page_start,
            page_end=list_block.page_end,
            metadata=list_block.metadata,
        )
        groups.append([DocumentBlock(block_type=BlockType.LIST, list_block=split_list)])
    return groups


def _group_heading_text(group: list[DocumentBlock]) -> str | None:
    for block in group:
        if block.heading is not None:
            return block.heading.text
    return None


def _build_block_context_map(
    sections: list[Section],
    parent_path: tuple[str, ...] = (),
) -> dict[int, BlockContext]:
    mapping: dict[int, BlockContext] = {}
    for section in sections:
        path = parent_path + (section.title,)
        context = BlockContext(
            section_title=section.title,
            section_number=section.section_number,
            heading_level=section.level,
            hierarchy_path=path,
        )
        for block in section.blocks:
            mapping[id(block)] = context
        mapping.update(_build_block_context_map(section.subsections, path))
    return mapping


def _resolve_group_context(
    group: list[DocumentBlock],
    context_map: dict[int, BlockContext],
) -> BlockContext:
    for block in group:
        context = context_map.get(id(block))
        if context is not None:
            return context
    return BlockContext(
        section_title=None,
        section_number=None,
        heading_level=None,
        hierarchy_path=(),
    )


def _is_first_chunk_for_section(
    group: list[DocumentBlock],
    all_groups: list[list[DocumentBlock]],
    order: int,
    context_map: dict[int, BlockContext],
) -> bool:
    context = _resolve_group_context(group, context_map)
    if context.section_title is None:
        return order == 0
    for prior in all_groups[:order]:
        prior_context = _resolve_group_context(prior, context_map)
        if prior_context.section_title == context.section_title:
            return False
    return True


def _resolve_chunk_type(
    blocks: list[DocumentBlock],
    *,
    has_heading: bool,
    hierarchy_path: tuple[str, ...],
) -> ChunkType:
    types = {block.block_type for block in blocks}
    if types == {BlockType.HEADING}:
        return ChunkType.SECTION_HEADER
    if types == {BlockType.PARAGRAPH}:
        return ChunkType.PARAGRAPH
    if types == {BlockType.TABLE}:
        return ChunkType.TABLE
    if types == {BlockType.LIST}:
        return ChunkType.LIST
    if has_heading and len(hierarchy_path) > 1:
        return ChunkType.SUBSECTION
    return ChunkType.MIXED


def _only_heading(blocks: list[DocumentBlock]) -> bool:
    return len(blocks) == 1 and blocks[0].block_type == BlockType.HEADING


def _group_page_range(blocks: list[DocumentBlock]) -> tuple[int | None, int | None]:
    starts: list[int] = []
    ends: list[int] = []
    for block in blocks:
        page_start, page_end = block_page_range(block)
        if page_start is not None:
            starts.append(page_start)
        if page_end is not None:
            ends.append(page_end)
    return (min(starts) if starts else None, max(ends) if ends else None)


def _infer_document_title(document: StructuredDocument) -> str | None:
    for block in document.blocks:
        if block.heading is not None and block.heading.level == 1:
            return block.heading.text
    if document.sections:
        return document.sections[0].title
    return document.source
