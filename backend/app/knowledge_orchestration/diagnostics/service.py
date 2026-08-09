"""Diagnostics helpers for orchestration."""

from __future__ import annotations

from app.knowledge_orchestration.models.types import OrchestrationResult
from app.knowledge_orchestration.registry.worker_registry import WorkerRegistry


class OrchestrationDiagnosticsService:
    def registry_snapshot(self, registry: WorkerRegistry) -> dict:
        return {
            "workers": registry.metadata(),
            "count": len(registry.list_workers()),
        }

    def summarize(self, result: OrchestrationResult) -> dict:
        return {
            "eligible": result.diagnostics.eligible_workers,
            "failed": result.diagnostics.failed_workers,
            "timeouts": result.diagnostics.timed_out_workers,
            "skipped": result.diagnostics.skipped_workers,
            "timeline": result.diagnostics.timeline,
            "merger": result.diagnostics.merger,
            "schedule": result.diagnostics.schedule,
        }
