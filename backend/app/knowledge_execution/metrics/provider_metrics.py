"""Provider metric helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.knowledge_execution.models.types import ProviderResult


@dataclass
class ProviderMetrics:
    executions: int = 0
    successes: int = 0
    failures: int = 0
    total_elapsed_ms: float = 0.0
    total_evidence: int = 0

    @property
    def success_rate(self) -> float:
        if self.executions == 0:
            return 0.0
        return self.successes / self.executions

    @property
    def failure_rate(self) -> float:
        if self.executions == 0:
            return 0.0
        return self.failures / self.executions

    @property
    def average_elapsed_ms(self) -> float:
        if self.executions == 0:
            return 0.0
        return self.total_elapsed_ms / self.executions

    @property
    def average_evidence_count(self) -> float:
        if self.executions == 0:
            return 0.0
        return self.total_evidence / self.executions

    def to_dict(self) -> dict:
        return {
            "executions": self.executions,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.success_rate, 4),
            "failure_rate": round(self.failure_rate, 4),
            "average_elapsed_ms": round(self.average_elapsed_ms, 4),
            "average_evidence_count": round(self.average_evidence_count, 4),
        }


@dataclass
class MetricsRegistry:
    by_provider: dict[str, ProviderMetrics] = field(default_factory=lambda: defaultdict(ProviderMetrics))

    def record(self, results: list[ProviderResult]) -> None:
        for result in results:
            metrics = self.by_provider[result.provider_name]
            metrics.executions += 1
            metrics.total_elapsed_ms += result.elapsed_ms
            metrics.total_evidence += len(result.evidence)
            if result.success:
                metrics.successes += 1
            else:
                metrics.failures += 1

    def snapshot(self) -> dict[str, dict]:
        return {name: metrics.to_dict() for name, metrics in sorted(self.by_provider.items())}
