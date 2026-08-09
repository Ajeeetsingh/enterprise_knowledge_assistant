"""Professional enterprise writing & visual hierarchy polish (Phase 5D).

Post-processes rendered markdown. Does not change RX selection, renderer
architecture, or adaptive component architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.response_experience.polish.callouts import apply_callouts
from app.response_experience.polish.emphasis import emphasize_markdown
from app.response_experience.polish.lists import convert_inline_lists
from app.response_experience.polish.sources import clean_source_sections
from app.response_experience.polish.spacing import (
    collapse_exact_duplicate_sentences,
    normalize_heading_hierarchy,
    normalize_spacing,
    split_long_paragraphs,
)
from app.response_experience.polish.summary import refine_executive_summary


@dataclass
class PolishResult:
    """Polished markdown plus observability."""

    markdown: str
    transforms_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transforms_applied": list(self.transforms_applied),
            "markdown_chars": len(self.markdown),
        }


def polish_enterprise_markdown(markdown: str) -> PolishResult:
    """Apply deterministic presentation polish without inventing facts."""
    original = markdown or ""
    text = original
    applied: list[str] = []

    steps: list[tuple[str, Any]] = [
        ("normalize_heading_hierarchy", normalize_heading_hierarchy),
        ("collapse_exact_duplicate_sentences", collapse_exact_duplicate_sentences),
        ("split_long_paragraphs", split_long_paragraphs),
        ("convert_inline_lists", convert_inline_lists),
        ("apply_callouts", apply_callouts),
        ("refine_executive_summary", refine_executive_summary),
        ("emphasize_scannable_terms", emphasize_markdown),
        ("clean_source_sections", clean_source_sections),
        ("normalize_spacing", normalize_spacing),
    ]

    for name, fn in steps:
        before = text
        text = fn(text)
        if text != before:
            applied.append(name)

    return PolishResult(markdown=text, transforms_applied=applied)
