"""Internal explainability types for metadata-aware retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetadataScoreBreakdown:
    """Explainability payload for a rescored candidate."""

    raw_cosine_score: float
    calibrated_cosine_score: float
    metadata_bonus: float
    final_score: float
    explanations: list[str] = field(default_factory=list)
    detected_intent: str = "general"
    chunk_type: str | None = None
