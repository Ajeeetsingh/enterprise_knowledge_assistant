"""Stable semantic chunk identifier generation."""

from __future__ import annotations

import hashlib
import re

from app.ingestion.structure.models import BlockType, DocumentBlock

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def block_key(block: DocumentBlock) -> str:
    """Return a stable key for a structured block."""
    if block.heading is not None:
        return f"h{block.heading.metadata.reading_order}"
    if block.paragraph is not None:
        return f"p{block.paragraph.metadata.reading_order}"
    if block.table is not None:
        return block.table.table_id
    if block.list_block is not None:
        return block.list_block.list_id
    return "unknown"


def stable_chunk_id(source: str, blocks: list[DocumentBlock]) -> str:
    """Build a chunk identifier that remains stable when other chunks change."""
    keys = [block_key(block) for block in blocks]
    joined = "-".join(keys)
    if len(joined) <= 120:
        return f"{source}::sem-{joined}"
    digest = hashlib.sha1(joined.encode("utf-8")).hexdigest()[:12]
    anchor = "-".join(keys[:2])
    safe_anchor = _SAFE_ID_RE.sub("-", anchor)[:40]
    return f"{source}::sem-{safe_anchor}-{digest}"
