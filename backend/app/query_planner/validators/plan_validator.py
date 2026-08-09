"""Validate QueryExecutionPlan completeness."""

from __future__ import annotations

from app.query_planner.enums import INDEX_NAMES, QueryIntent, RetrievalStrategy
from app.query_planner.models.types import QueryExecutionPlan


class PlanValidator:
    def validate(self, plan: QueryExecutionPlan) -> list[str]:
        errors: list[str] = []
        if not plan.plan_id:
            errors.append("missing_plan_id")
        if not plan.normalized_query and not plan.raw_query:
            errors.append("missing_query")
        if not plan.primary_intent:
            errors.append("missing_intent")
        elif plan.primary_intent not in {item.value for item in QueryIntent}:
            errors.append("invalid_intent")
        if not plan.required_indexes:
            errors.append("missing_required_indexes")
        else:
            for name in plan.required_indexes:
                if name not in INDEX_NAMES:
                    errors.append(f"unknown_index:{name}")
        if not plan.preferred_strategy:
            errors.append("missing_strategy")
        elif plan.preferred_strategy not in {item.value for item in RetrievalStrategy}:
            # Allow forward-compatible labels but warn via diagnostics note
            plan.diagnostics.notes.append(f"non_enum_strategy:{plan.preferred_strategy}")
        if not plan.fallback_strategy:
            errors.append("missing_fallback")
        if not plan.expected_output:
            errors.append("missing_expected_output")
        if not plan.planner_version:
            errors.append("missing_planner_version")
        if plan.confidence < 0 or plan.confidence > 1:
            errors.append("confidence_out_of_range")
        if errors:
            plan.diagnostics.planning_failures.extend(errors)
            plan.status = "invalid"
            plan.warnings.append("Plan failed validation.")
        return errors
