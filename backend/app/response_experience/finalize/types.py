"""Types for Phase 5E finalize pass."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.response_experience.finalize.validate import MarkdownValidation


@dataclass
class FinalizeResult:
    markdown: str
    transforms_applied: list[str] = field(default_factory=list)
    empty_sections_removed: int = 0
    validation_ok: bool = True
    validation_issues: list[str] = field(default_factory=list)
    content_preserved: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "transforms_applied": list(self.transforms_applied),
            "empty_sections_removed": self.empty_sections_removed,
            "validation_ok": self.validation_ok,
            "validation_issues": list(self.validation_issues),
            "content_preserved": self.content_preserved,
            "markdown_chars": len(self.markdown),
        }
