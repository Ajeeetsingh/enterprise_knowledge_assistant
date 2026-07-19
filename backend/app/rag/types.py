"""Shared RAG types."""

from __future__ import annotations

from dataclasses import asdict, dataclass

CITATION_EXCERPT_LENGTH = 200
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Confidence calibration parameters.
# Raw cosine similarity for relevant matches typically falls in [0.3, 0.95].
# We linearly rescale [LOW, HIGH] → [0, 1] so that a mediocre match (low
# similarity) reads as low confidence and a strong match reads as high confidence.
_CALIBRATION_LOW = 0.15   # raw score mapped to 0% confidence
_CALIBRATION_HIGH = 0.90  # raw score mapped to 100% confidence
_CALIBRATION_RANGE = _CALIBRATION_HIGH - _CALIBRATION_LOW


def calibrate_confidence(raw_score: float) -> float:
    """Map a raw cosine similarity score to a calibrated [0, 1] confidence value.

    Uses a linear rescaling so that:
    * raw ≤ 0.15 → 0 %
    * raw = 0.525 → ~50 %
    * raw ≥ 0.90 → 100 %

    This avoids the raw score (which is a unit-less geometric angle) being
    presented directly as a percentage to end users.
    """
    calibrated = (raw_score - _CALIBRATION_LOW) / _CALIBRATION_RANGE
    return round(max(0.0, min(1.0, calibrated)), 4)


@dataclass
class RetrievalResult:
    """A single semantic retrieval hit."""

    content: str
    source: str
    category: str
    confidence: float
    chunk_id: str
    page_number: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    section_title: str | None = None
    hierarchy_path: tuple[str, ...] | None = None
    raw_cosine_score: float | None = None
    metadata_bonus: float | None = None
    final_score: float | None = None
    score_explanation: list[str] | None = None
    detected_intent: str | None = None
    chunk_type: str | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None
    fusion_score: float | None = None
    fusion_explanation: list[str] | None = None
    source_retrievers: list[str] | None = None
    reranker_score: float | None = None
    final_rank: int | None = None


@dataclass
class Citation:
    source: str
    excerpt: str
    confidence: float
    page: int | None = None


@dataclass
class QueryResponse:
    query: str
    role: str
    routed_category: str
    route_confidence: float
    answer: str
    sources_used: list[str]
    citations: list[Citation]
    confidence_score: float
    access_granted: bool
    message: str

    def to_dict(self) -> dict:
        return asdict(self)
