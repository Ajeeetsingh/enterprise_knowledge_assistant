"""Text chunking for document ingestion with page tracking and semantic boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Larger chunks preserve more context; overlap prevents splitting mid-sentence
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Sentinel embedded by PDF parser to record page boundaries in extracted text
PAGE_MARKER_PATTERN = re.compile(r"<<<PAGE:(\d+)>>>")


@dataclass
class DocumentChunk:
    """A searchable chunk derived from a source document."""

    chunk_id: str
    content: str
    source: str
    category: str
    chunk_index: int
    page_number: int | None = None
    metadata: object | None = None


def _split_into_sentences(text: str) -> list[str]:
    """Split text at sentence boundaries, preserving newlines as boundaries too."""
    # First normalise so paragraph separators are explicit sentence ends
    text = re.sub(r"\n{2,}", " @@PARA@@ ", text)
    # Split on sentence-ending punctuation followed by whitespace
    raw = re.split(r"(?<=[.!?])\s+", text)
    sentences: list[str] = []
    for part in raw:
        for sub in part.split("@@PARA@@"):
            cleaned = sub.strip()
            if cleaned:
                sentences.append(cleaned)
    return sentences


def chunk_text(
    text: str,
    source: str,
    category: str,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """Split text into overlapping chunks, preserving page and sentence boundaries.

    Page markers (``<<<PAGE:N>>>``) emitted by the PDF parser are stripped from
    chunk content but used to assign a ``page_number`` to each chunk.
    """
    if not text or not text.strip():
        return []

    # --- parse page markers and build (page_number, line) pairs ---------------
    current_page: int | None = None
    annotated_lines: list[tuple[int | None, str]] = []

    for raw_line in text.split("\n"):
        marker = PAGE_MARKER_PATTERN.match(raw_line.strip())
        if marker:
            current_page = int(marker.group(1))
            continue
        line = raw_line.strip()
        if line:
            annotated_lines.append((current_page, line))

    if not annotated_lines:
        return []

    # --- normalise whitespace within lines and combine with page info ----------
    # We work on a list of (page, sentence) so we can assign page per chunk
    sentences: list[tuple[int | None, str]] = []
    for page, line in annotated_lines:
        for sentence in _split_into_sentences(line):
            if sentence.strip():
                sentences.append((page, sentence.strip()))

    if not sentences:
        return []

    # --- greedily build chunks, breaking on sentence/paragraph boundaries ------
    chunks: list[DocumentChunk] = []
    i = 0
    chunk_index = 0

    while i < len(sentences):
        chunk_sentences: list[tuple[int | None, str]] = []
        char_count = 0
        j = i

        while j < len(sentences):
            page, sentence = sentences[j]
            new_count = char_count + len(sentence) + 1  # +1 for space
            if new_count > chunk_size and chunk_sentences:
                # Only break if we already have content
                break
            chunk_sentences.append((page, sentence))
            char_count = new_count
            j += 1

        if not chunk_sentences:
            # Single sentence longer than chunk_size — include it anyway
            chunk_sentences = [sentences[i]]
            j = i + 1

        content = " ".join(s for _, s in chunk_sentences).strip()
        # Assign the page number of the first sentence in this chunk
        chunk_page = chunk_sentences[0][0]

        if content:
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{source}::{chunk_index}",
                    content=content,
                    source=source,
                    category=category,
                    chunk_index=chunk_index,
                    page_number=chunk_page,
                )
            )
            chunk_index += 1

        # Advance with overlap: step back ~chunk_overlap chars worth of sentences
        if j >= len(sentences):
            break

        # Find overlap start: step back until we've rewound ≥ chunk_overlap chars
        overlap_chars = 0
        overlap_start = j - 1
        while overlap_start > i and overlap_chars < chunk_overlap:
            overlap_chars += len(chunk_sentences[-(j - overlap_start)][1])
            overlap_start -= 1

        i = max(i + 1, overlap_start)

    return chunks
