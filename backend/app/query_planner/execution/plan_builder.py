"""Assemble canonical QueryExecutionPlan objects."""

from __future__ import annotations

import uuid

from app.query_planner.analyzers.query_analyzer import QueryAnalysis
from app.query_planner.enums import QueryIntent
from app.query_planner.models.types import (
    IntentCandidate,
    PlannerDiagnostics,
    QueryConstraints,
    QueryExecutionPlan,
    utc_now_iso,
)
from app.query_planner.parser.normalizer import NormalizationResult
from app.query_planner.version import QUERY_PLANNER_PIPELINE_VERSION


class ExecutionPlanBuilder:
    def build(
        self,
        *,
        raw_query: str,
        normalization: NormalizationResult,
        intents: list[IntentCandidate],
        analysis: QueryAnalysis,
        constraints: QueryConstraints,
        required_indexes: list[str],
        relationship_requirements: list[str],
        preferred_strategy: str,
        fallback_strategy: str,
        expected_output: str,
        available_indexes: set[str] | None,
        timeline_ms: dict[str, float],
    ) -> QueryExecutionPlan:
        primary = intents[0] if intents else IntentCandidate(
            intent=QueryIntent.UNKNOWN.value, confidence=0.0
        )
        warnings: list[str] = []
        diagnostics = PlannerDiagnostics(timeline_ms=dict(timeline_ms))

        if len(intents) >= 2 and abs(intents[0].confidence - intents[1].confidence) < 0.08:
            diagnostics.intent_confusion.append(
                f"{intents[0].intent} vs {intents[1].intent}"
            )
            warnings.append("Multiple intents have similar confidence.")

        if primary.intent == QueryIntent.UNKNOWN.value:
            warnings.append("Intent classified as UNKNOWN — fallback strategy recommended.")

        missing = []
        if available_indexes is not None:
            missing = [name for name in required_indexes if name not in available_indexes]
            diagnostics.missing_indexes = missing
            if missing:
                warnings.append(f"Missing indexes in manager: {', '.join(missing)}")

        unsupported = []
        if constraints.before or constraints.after:
            unsupported.append("date_range_not_indexed")
        diagnostics.unsupported_constraints = unsupported
        if unsupported:
            warnings.append("Some constraints are recognized but not backed by Hybrid Indexes yet.")

        filters: dict = {}
        if constraints.department:
            filters["department"] = constraints.department
        if constraints.collection:
            filters["collection"] = constraints.collection
        if constraints.document_type:
            filters["document_type"] = constraints.document_type
        if constraints.language:
            filters["language"] = constraints.language
        if constraints.exact_filename:
            filters["exact_filename"] = constraints.exact_filename
        if constraints.partial_filename:
            filters["partial_filename"] = constraints.partial_filename
        if constraints.entity_filters:
            filters["entities"] = list(constraints.entity_filters)
        if constraints.taxonomy_path:
            filters["taxonomy_path"] = constraints.taxonomy_path
        if constraints.version_label:
            filters["version_label"] = constraints.version_label
        if constraints.latest:
            filters["latest"] = True
        if constraints.oldest:
            filters["oldest"] = True

        sort: list[str] = []
        if constraints.latest:
            sort.append("version_rank:desc")
        elif constraints.oldest:
            sort.append("version_rank:asc")
        if constraints.after or constraints.before:
            sort.append("upload_date")

        if normalization.aliases_applied:
            diagnostics.notes.append(
                "aliases_applied="
                + ",".join(f"{a['alias']}→{a['canonical']}" for a in normalization.aliases_applied)
            )

        return QueryExecutionPlan(
            plan_id=str(uuid.uuid4()),
            raw_query=raw_query,
            normalized_query=normalization.normalized,
            intents=intents,
            primary_intent=primary.intent,
            confidence=float(primary.confidence),
            entities=list(analysis.entities),
            constraints=constraints,
            required_indexes=required_indexes,
            relationship_requirements=relationship_requirements,
            preferred_strategy=preferred_strategy,
            fallback_strategy=fallback_strategy,
            expected_output=expected_output,
            filters=filters,
            sort=sort,
            warnings=warnings,
            diagnostics=diagnostics,
            planner_version=QUERY_PLANNER_PIPELINE_VERSION,
            created_at=utc_now_iso(),
            status="ok" if not missing else "degraded",
        )
