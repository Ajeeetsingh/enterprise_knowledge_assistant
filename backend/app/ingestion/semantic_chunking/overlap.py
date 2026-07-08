"""Semantic overlap helpers."""

from __future__ import annotations

from app.ingestion.semantic_chunking.config import SemanticChunkingSettings


def apply_semantic_overlap(
    content: str,
    *,
    section_title: str | None,
    hierarchy_path: tuple[str, ...],
    settings: SemanticChunkingSettings,
    is_first_chunk_in_section: bool,
    context_heading: str | None = None,
) -> str:
    """Prepend contextual headings for semantic overlap when appropriate."""
    if not settings.semantic_overlap_enabled or is_first_chunk_in_section:
        return content

    prefixes: list[str] = []
    if settings.include_hierarchy_in_overlap and hierarchy_path:
        prefixes.append(" > ".join(hierarchy_path))
    elif section_title:
        prefixes.append(section_title)

    if context_heading:
        heading = context_heading.strip()
        if heading and heading not in content and heading not in prefixes:
            prefixes.append(heading)

    if not prefixes:
        return content

    prefix = "\n".join(prefixes)
    if content.startswith(prefix):
        return content
    return f"{prefix}\n\n{content}"
