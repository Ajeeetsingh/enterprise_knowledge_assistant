"""Phase 5E — final UX polish & consistency pass.

Runs after Phase 5D polish. Structural/presentation only; no answer-content
invention and no changes to RX / renderer / adaptive / 5D rule modules.
"""

from __future__ import annotations

from typing import Callable

from app.response_experience.finalize.edge_cases import polish_edge_cases
from app.response_experience.finalize.empty_sections import remove_empty_sections
from app.response_experience.finalize.headings import normalize_headings
from app.response_experience.finalize.lists import normalize_lists
from app.response_experience.finalize.separators import normalize_separators
from app.response_experience.finalize.sources import normalize_source_sections
from app.response_experience.finalize.spacing import normalize_spacing
from app.response_experience.finalize.tables import normalize_tables
from app.response_experience.finalize.types import FinalizeResult
from app.response_experience.finalize.validate import validate_markdown
from app.response_experience.markdown.renderer import content_preserved


def finalize_enterprise_markdown(markdown: str) -> FinalizeResult:
    """Apply deterministic consistency cleanup to polished markdown."""
    original = markdown or ""
    text = original
    applied: list[str] = []
    empty_removed = 0

    text, removed = remove_empty_sections(text)
    if removed:
        applied.append("remove_empty_sections")
        empty_removed += removed

    steps: list[tuple[str, Callable[[str], str]]] = [
        ("normalize_headings", normalize_headings),
        ("normalize_lists", normalize_lists),
        ("normalize_tables", normalize_tables),
        ("normalize_source_sections", normalize_source_sections),
        ("normalize_separators", normalize_separators),
        ("polish_edge_cases", polish_edge_cases),
        ("normalize_spacing", normalize_spacing),
    ]

    for name, fn in steps:
        before = text
        text = fn(text)
        if text != before:
            applied.append(name)

    # Second empty-section pass after sources/tables may clear sections.
    text, removed = remove_empty_sections(text)
    if removed:
        if "remove_empty_sections" not in applied:
            applied.append("remove_empty_sections")
        empty_removed += removed
        # Re-normalize spacing after removals.
        spaced = normalize_spacing(text)
        if spaced != text:
            text = spaced
            if "normalize_spacing" not in applied:
                applied.append("normalize_spacing")

    validation = validate_markdown(text)
    # Empty-section removal is intentional presentation cleanup; compare against
    # an empty-stripped baseline so placeholders do not fail preservation.
    baseline, _ = remove_empty_sections(original)
    preserved = content_preserved(baseline, text) if baseline.strip() else True

    return FinalizeResult(
        markdown=text,
        transforms_applied=applied,
        empty_sections_removed=empty_removed,
        validation_ok=validation.ok,
        validation_issues=list(validation.issues),
        content_preserved=preserved,
    )
