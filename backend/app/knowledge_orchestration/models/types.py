"""Orchestration domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class WorkerCapability:
    name: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerHealth:
    status: str = "healthy"
    detail: str = ""
    checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerEvidence:
    """Evidence produced by a single worker (wraps provider evidence)."""

    worker_id: str
    success: bool
    evidence_items: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0
    error: str | None = None
    timed_out: bool = False
    skipped: bool = False
    diagnostics: dict[str, Any] = field(default_factory=dict)
    source_attribution: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScheduledWorker:
    worker_id: str
    group: int
    depends_on: list[str] = field(default_factory=list)
    timeout_ms: float = 2000.0
    parallel: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionSchedule:
    workers: list[ScheduledWorker] = field(default_factory=list)
    groups: list[list[str]] = field(default_factory=list)
    budget_ms: float = 10000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "workers": [item.to_dict() for item in self.workers],
            "groups": self.groups,
            "budget_ms": self.budget_ms,
        }


@dataclass
class MergerReport:
    input_evidence_count: int = 0
    output_evidence_count: int = 0
    duplicates_removed: int = 0
    conflicts_resolved: int = 0
    sources: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrchestrationDiagnostics:
    eligible_workers: list[str] = field(default_factory=list)
    skipped_workers: list[str] = field(default_factory=list)
    failed_workers: list[str] = field(default_factory=list)
    timed_out_workers: list[str] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    schedule: dict[str, Any] = field(default_factory=dict)
    merger: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrchestrationResult:
    orchestration_id: str
    plan_id: str
    raw_query: str
    worker_evidence: list[WorkerEvidence] = field(default_factory=list)
    candidate_evidence_set: dict[str, Any] = field(default_factory=dict)
    diagnostics: OrchestrationDiagnostics = field(default_factory=OrchestrationDiagnostics)
    elapsed_ms: float = 0.0
    status: str = "ok"
    orchestrator_version: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "orchestration_id": self.orchestration_id,
            "plan_id": self.plan_id,
            "raw_query": self.raw_query,
            "worker_evidence": [item.to_dict() for item in self.worker_evidence],
            "candidate_evidence_set": self.candidate_evidence_set,
            "diagnostics": self.diagnostics.to_dict(),
            "elapsed_ms": self.elapsed_ms,
            "status": self.status,
            "orchestrator_version": self.orchestrator_version,
            "created_at": self.created_at,
        }
