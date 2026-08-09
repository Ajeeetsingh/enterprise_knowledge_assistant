"""Types for adaptive enterprise components (Phase 5C)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.response_experience.enums import ResponseComponent


@dataclass
class ComponentBuildResult:
    """Outcome of building one adaptive component."""

    component: ResponseComponent
    markdown: str | None
    skipped: bool
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "chars": len(self.markdown or ""),
        }


@dataclass
class AdaptiveEnrichment:
    """Merged content + observability for Phase 5C."""

    content_map: dict[ResponseComponent, str]
    components_requested: list[ResponseComponent] = field(default_factory=list)
    build_results: list[ComponentBuildResult] = field(default_factory=list)

    @property
    def skip_reasons(self) -> dict[str, str]:
        return {
            item.component.value: item.skip_reason
            for item in self.build_results
            if item.skipped and item.skip_reason
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "components_requested": [item.value for item in self.components_requested],
            "skip_reasons": self.skip_reasons,
            "builds": [item.to_dict() for item in self.build_results],
        }
