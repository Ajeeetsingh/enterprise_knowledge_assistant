"""Canonical evidence and candidate models for Phase 13.6."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class EvidenceItem:
    """Single piece of evidence from a Hybrid Knowledge Index lookup."""

    knowledge_id: str
    document_id: str
    source_index: str
    matched_field: str
    match_type: str
    confidence: float
    evidence_score: float
    explanation: str
    metadata: dict[str, Any] = field(default_factory=dict)
    relationship_context: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderResult:
    provider_name: str
    success: bool
    evidence: list[EvidenceItem] = field(default_factory=list)
    elapsed_ms: float = 0.0
    error: str | None = None
    query_used: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "success": self.success,
            "evidence": [item.to_dict() for item in self.evidence],
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
            "query_used": self.query_used,
        }


@dataclass
class ScoreContribution:
    factor: str
    points: float
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateDocument:
    document_id: str
    knowledge_id: str
    rank: int = 0
    score: float = 0.0
    confidence: float = 0.0
    supporting_indexes: list[str] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)
    score_contributions: list[ScoreContribution] = field(default_factory=list)
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "knowledge_id": self.knowledge_id,
            "rank": self.rank,
            "score": self.score,
            "confidence": self.confidence,
            "supporting_indexes": self.supporting_indexes,
            "evidence": [item.to_dict() for item in self.evidence],
            "score_contributions": [item.to_dict() for item in self.score_contributions],
            "explanation": self.explanation,
            "metadata": self.metadata,
        }


@dataclass
class EvidenceGraphEdge:
    source_document_id: str
    target_document_id: str
    relationship_type: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionDiagnostics:
    providers_selected: list[str] = field(default_factory=list)
    providers_succeeded: list[str] = field(default_factory=list)
    providers_failed: list[str] = field(default_factory=list)
    provider_timeline_ms: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionStatistics:
    execution_latency_ms: float = 0.0
    providers_executed: int = 0
    evidence_collected: int = 0
    candidates_generated: int = 0
    average_candidate_score: float = 0.0
    failures: int = 0
    parallel: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateEvidenceSet:
    """Structured output of the Knowledge Execution Engine."""

    execution_id: str
    plan_id: str
    raw_query: str
    normalized_query: str
    candidates: list[CandidateDocument] = field(default_factory=list)
    evidence_graph: list[EvidenceGraphEdge] = field(default_factory=list)
    provider_results: list[ProviderResult] = field(default_factory=list)
    statistics: ExecutionStatistics = field(default_factory=ExecutionStatistics)
    diagnostics: ExecutionDiagnostics = field(default_factory=ExecutionDiagnostics)
    ranking: list[str] = field(default_factory=list)
    confidence: float = 0.0
    engine_version: str = ""
    created_at: str = ""
    status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "plan_id": self.plan_id,
            "raw_query": self.raw_query,
            "normalized_query": self.normalized_query,
            "candidates": [item.to_dict() for item in self.candidates],
            "evidence_graph": [item.to_dict() for item in self.evidence_graph],
            "provider_results": [item.to_dict() for item in self.provider_results],
            "statistics": self.statistics.to_dict(),
            "diagnostics": self.diagnostics.to_dict(),
            "ranking": self.ranking,
            "confidence": self.confidence,
            "engine_version": self.engine_version,
            "created_at": self.created_at,
            "status": self.status,
        }
