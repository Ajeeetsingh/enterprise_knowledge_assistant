"""Validate orchestration results."""

from __future__ import annotations

from app.knowledge_orchestration.models.types import OrchestrationResult


class OrchestrationValidator:
    def validate(self, result: OrchestrationResult) -> list[str]:
        errors: list[str] = []
        if not result.orchestration_id:
            errors.append("missing_orchestration_id")
        if not result.plan_id:
            errors.append("missing_plan_id")
        if not result.orchestrator_version:
            errors.append("missing_version")
        if errors:
            result.status = "invalid"
            result.diagnostics.notes.extend(errors)
        return errors
