"""Semantic chunk validation."""

from __future__ import annotations

import re

from app.ingestion.semantic_chunking.assembler import AssembledChunk
from app.ingestion.semantic_chunking.renderers import render_block
from app.ingestion.structure.models import StructuredDocument

_WHITESPACE_RE = re.compile(r"\s+")


def validate_semantic_chunks(
    document: StructuredDocument,
    chunks: list[AssembledChunk],
) -> list[str]:
    """Validate semantic chunk generation output."""
    issues: list[str] = []

    source_blocks = list(document.blocks)
    assigned_blocks: list[str] = []
    seen_ids: set[str] = set()
    reading_orders: list[int] = []

    for chunk in chunks:
        if chunk.chunk_id in seen_ids:
            issues.append(f"Duplicate chunk id: {chunk.chunk_id}")
        seen_ids.add(chunk.chunk_id)
        reading_orders.append(chunk.metadata.reading_order)
        assigned_blocks.extend(chunk.metadata.block_keys)

    if reading_orders != sorted(reading_orders):
        issues.append("Chunk reading order is not monotonic.")

    expected_keys = [_block_key_from_document(block) for block in source_blocks]
    if len(assigned_blocks) != len(expected_keys):
        issues.append(
            f"Block assignment mismatch: expected {len(expected_keys)} assigned {len(assigned_blocks)}."
        )
    else:
        if assigned_blocks != expected_keys:
            issues.append("Block reading order does not match structured document order.")

    if len(set(assigned_blocks)) != len(assigned_blocks):
        issues.append("Duplicate block assignment detected.")

    source_text = _normalize_for_coverage(
        " ".join(render_block(block) for block in source_blocks)
    )
    chunk_text = _normalize_for_coverage(" ".join(chunk.content for chunk in chunks))
    if source_text and chunk_text:
        source_tokens = set(source_text.split())
        chunk_tokens = set(chunk_text.split())
        missing_ratio = len(source_tokens - chunk_tokens) / max(len(source_tokens), 1)
        if missing_ratio > 0.20:
            issues.append(
                f"Potential content loss detected ({missing_ratio:.1%} source tokens missing)."
            )

    return issues


def _block_key_from_document(block) -> str:
    from app.ingestion.semantic_chunking.ids import block_key

    return block_key(block)


def _normalize_for_coverage(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.strip().lower())
