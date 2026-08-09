"""Phase 5C — Adaptive enterprise components."""

from app.response_experience.components.adaptive import (
    enrich_with_adaptive_components,
    requested_components,
)
from app.response_experience.components.types import AdaptiveEnrichment, ComponentBuildResult

__all__ = [
    "AdaptiveEnrichment",
    "ComponentBuildResult",
    "enrich_with_adaptive_components",
    "requested_components",
]
