"""Shared RAG types."""

from __future__ import annotations

from dataclasses import asdict, dataclass

CITATION_EXCERPT_LENGTH = 200


@dataclass
class Citation:
    source: str
    excerpt: str
    confidence: float


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
