"""Heading-aware text construction for retrieval models.

Chunk ``content`` is never mutated by this module — it stays exactly as
assembled by semantic chunking for display, citations, and the LLM context
window. Instead, this module derives a *separate* text representation used
only as input to the embedding model, the BM25 tokenizer, and the
cross-encoder reranker, so a chunk's section heading carries materially
more semantic weight than a single incidental mention buried inside a
longer body would.

Why this exists
----------------
Enterprise documents frequently contain multiple sections that are
topically adjacent but semantically distinct, e.g.:

    "Who are the main issuers?"   vs   "Who are the main investors?"
    "Strategic priorities"        vs   "Strategic initiatives"
    "Risk governance"             vs   "Risk management"

The prose *body* of such sections is often lexically and semantically very
similar (both describe the same market/program from a different angle);
the heading is frequently the *only* reliable signal that distinguishes
them. Embedding/BM25/reranker models that see the heading only once,
diluted inside a much longer body, can easily confuse the two sections.
Repeating the heading ahead of the body gives every downstream retrieval
stage a stronger, consistent signal — without touching chunk boundaries,
the embedding model, the BM25 algorithm, or the cross-encoder model itself.
"""

from __future__ import annotations

DEFAULT_HEADING_REPETITIONS = 2


def resolve_chunk_heading(
    section_title: str | None,
    hierarchy_path: tuple[str, ...] | None = None,
) -> str | None:
    """Return the most specific known heading for a chunk, if any.

    Prefers the chunk's own section title; falls back to the most specific
    (last) segment of its hierarchy path when no section title is known.
    """
    if section_title:
        return section_title
    if hierarchy_path:
        return hierarchy_path[-1] or None
    return None


def build_retrieval_text(
    content: str,
    heading: str | None,
    *,
    repetitions: int = DEFAULT_HEADING_REPETITIONS,
) -> str:
    """Return heading-weighted text for embedding/BM25/reranker input.

    The heading is repeated ``repetitions`` times ahead of the body so
    term-frequency-based (BM25) and mean-pooled dense representations give
    it materially more weight than a single mention would. Falls back to
    ``content`` unchanged when no heading is known or repetitions is 0.
    """
    heading = (heading or "").strip()
    if not heading or repetitions <= 0:
        return content
    prefix = "\n".join([heading] * repetitions)
    return f"{prefix}\n\n{content}"
