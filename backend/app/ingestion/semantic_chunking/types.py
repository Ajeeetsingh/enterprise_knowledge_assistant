"""Semantic chunk types and metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ChunkType(str, Enum):
    """Explicit semantic chunk classifications."""

    SECTION_HEADER = "section_header"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    SUBSECTION = "subsection"
    MIXED = "mixed"


@dataclass(frozen=True)
class ChunkMetadata:
    """Rich metadata attached to each semantic chunk."""

    chunk_type: ChunkType
    section_title: str | None = None
    section_number: str | None = None
    heading_level: int | None = None
    document_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    reading_order: int = 0
    contains_table: bool = False
    contains_list: bool = False
    contains_heading: bool = False
    paragraph_count: int = 0
    table_count: int = 0
    list_count: int = 0
    word_count: int = 0
    character_count: int = 0
    hierarchy_path: tuple[str, ...] = field(default_factory=tuple)
    block_keys: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class SemanticChunkStats:
    """Structured metrics from a semantic chunking run."""

    chunks_created: int = 0
    average_chunk_size: float = 0.0
    median_chunk_size: float = 0.0
    largest_chunk: int = 0
    smallest_chunk: int = 0
    average_words: float = 0.0
    average_paragraphs: float = 0.0
    average_tables: float = 0.0
    chunk_type_distribution: dict[str, int] = field(default_factory=dict)
    duration_ms: float = 0.0
