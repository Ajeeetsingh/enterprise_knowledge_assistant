"""Orchestration metrics helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.knowledge_orchestration.models.types import WorkerEvidence


@dataclass
class WorkerRuntimeMetrics:
    executions: int = 0
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    skipped: int = 0
    total_elapsed_ms: float = 0.0
    total_evidence: int = 0

    def to_dict(self) -> dict:
        return {
            "executions": self.executions,
            "successes": self.successes,
            "failures": self.failures,
            "timeouts": self.timeouts,
            "skipped": self.skipped,
            "success_rate": round(self.successes / self.executions, 4) if self.executions else 0.0,
            "average_elapsed_ms": (
                round(self.total_elapsed_ms / self.executions, 4) if self.executions else 0.0
            ),
            "average_evidence_count": (
                round(self.total_evidence / self.executions, 4) if self.executions else 0.0
            ),
        }


@dataclass
class OrchestrationMetrics:
    by_worker: dict[str, WorkerRuntimeMetrics] = field(
        default_factory=lambda: defaultdict(WorkerRuntimeMetrics)
    )

    def record(self, evidence: list[WorkerEvidence]) -> None:
        for item in evidence:
            metrics = self.by_worker[item.worker_id]
            metrics.executions += 1
            metrics.total_elapsed_ms += item.elapsed_ms
            metrics.total_evidence += len(item.evidence_items)
            if item.skipped:
                metrics.skipped += 1
            elif item.timed_out:
                metrics.timeouts += 1
                metrics.failures += 1
            elif item.success:
                metrics.successes += 1
            else:
                metrics.failures += 1

    def snapshot(self) -> dict[str, dict]:
        return {name: metrics.to_dict() for name, metrics in sorted(self.by_worker.items())}
