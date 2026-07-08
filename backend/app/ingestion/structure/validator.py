"""Structure extraction validation."""

from __future__ import annotations

import re

from app.ingestion.structure.models import BlockType, DocumentBlock, StructuredDocument

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_for_coverage(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().lower())


def _collect_block_text(blocks: list[DocumentBlock]) -> str:
    parts: list[str] = []
    for block in blocks:
        if block.block_type == BlockType.PARAGRAPH and block.paragraph is not None:
            parts.append(block.paragraph.text)
        elif block.block_type == BlockType.HEADING and block.heading is not None:
            parts.append(block.heading.text)
        elif block.block_type == BlockType.TABLE and block.table is not None:
            parts.append(" ".join(block.table.headers))
            for row in block.table.rows:
                parts.append(" ".join(row))
        elif block.block_type == BlockType.LIST and block.list_block is not None:
            parts.extend(_collect_list_text(block.list_block.items))
    return " ".join(parts)


def _collect_list_text(items) -> list[str]:
    texts: list[str] = []
    for item in items:
        texts.append(item.text)
        texts.extend(_collect_list_text(item.children))
    return texts


def validate_structure(document: StructuredDocument) -> list[str]:
    """Validate extracted structure and return human-readable issues."""
    issues: list[str] = []

    reading_orders = []
    seen_ids: set[str] = set()
    for block in document.blocks:
        metadata = None
        if block.paragraph is not None:
            metadata = block.paragraph.metadata
        elif block.heading is not None:
            metadata = block.heading.metadata
        elif block.table is not None:
            metadata = block.table.metadata
            if block.table.table_id in seen_ids:
                issues.append(f"Duplicate table id: {block.table.table_id}")
            seen_ids.add(block.table.table_id)
        elif block.list_block is not None:
            metadata = block.list_block.metadata
            if block.list_block.list_id in seen_ids:
                issues.append(f"Duplicate list id: {block.list_block.list_id}")
            seen_ids.add(block.list_block.list_id)

        if metadata is not None:
            reading_orders.append(metadata.reading_order)

    if reading_orders != sorted(reading_orders):
        issues.append("Reading order is not monotonic.")

    if len(reading_orders) != len(set(reading_orders)):
        issues.append("Duplicate reading order values detected.")

    source_without_markers = re.sub(r"<<<PAGE:\d+>>>", " ", document.raw_text)
    source_normalized = _normalize_for_coverage(source_without_markers)
    extracted_normalized = _normalize_for_coverage(_collect_block_text(document.blocks))

    if extracted_normalized and source_normalized:
        extracted_tokens = set(extracted_normalized.split())
        source_tokens = set(source_normalized.split())
        missing_ratio = len(source_tokens - extracted_tokens) / max(len(source_tokens), 1)
        if missing_ratio > 0.35:
            issues.append(
                f"Potential content loss detected ({missing_ratio:.1%} source tokens missing)."
            )

    if not document.sections:
        issues.append("No sections detected.")

    return issues
