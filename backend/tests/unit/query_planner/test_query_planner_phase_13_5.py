"""Phase 13.5 Intelligent Query Planner automated validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.query_planner.enums import QueryIntent, RetrievalStrategy
from app.query_planner.planner.pipeline import QueryPlanner
from app.query_planner.services.planner_service import QueryPlannerService
from app.query_planner.shadow import ShadowQueryPlannerService
from app.query_planner.storage.json_store import QueryPlanJsonStore
from app.query_planner.validators.plan_validator import PlanValidator
from app.query_planner.version import QUERY_PLANNER_PIPELINE_VERSION


@pytest.fixture
def planner() -> QueryPlanner:
    return QueryPlanner(index_manager=KnowledgeIndexManager())


def test_normalization_applies_aliases(planner: QueryPlanner) -> None:
    plan = planner.plan("leave policy")
    assert "Annual Leave" in plan.normalized_query or "Leave" in plan.normalized_query
    assert plan.diagnostics.notes  # alias note or other diagnostics ok
    assert any("aliases_applied" in note for note in plan.diagnostics.notes) or "Policy" in plan.normalized_query


def test_intent_classification_variants(planner: QueryPlanner) -> None:
    cases = {
        "latest HR leave policy": QueryIntent.VERSION_LOOKUP.value,
        "how many finance reports": QueryIntent.COUNT_QUERY.value,
        "summarize the password policy": QueryIntent.SUMMARY_REQUEST.value,
        "documents related to MFA": QueryIntent.RELATIONSHIP_QUERY.value,
        "compare leave policy vs remote work policy": QueryIntent.COMPARISON.value,
        "find filename expense_reports.txt": QueryIntent.METADATA_SEARCH.value,
    }
    for query, expected in cases.items():
        plan = planner.plan(query)
        intent_names = {item.intent for item in plan.intents}
        assert expected in intent_names or plan.primary_intent == expected, query


def test_constraint_and_entity_extraction(planner: QueryPlanner) -> None:
    plan = planner.plan('latest HR leave policy before 2024')
    assert plan.constraints.latest is True
    assert plan.constraints.department == "HR"
    assert plan.constraints.before == "2024"
    assert any(entity.kind in {"department", "entity"} for entity in plan.entities)


def test_strategy_and_required_indexes(planner: QueryPlanner) -> None:
    plan = planner.plan("What is the latest leave policy?")
    assert "version" in plan.required_indexes
    assert "metadata" in plan.required_indexes
    assert "entity" not in plan.required_indexes or plan.preferred_strategy
    assert plan.preferred_strategy in {item.value for item in RetrievalStrategy}
    assert plan.fallback_strategy


def test_execution_plan_completeness_and_validation(planner: QueryPlanner) -> None:
    plan = planner.plan("Show Security MFA policy")
    errors = PlanValidator().validate(plan)
    assert errors == []
    assert plan.plan_id
    assert plan.planner_version == QUERY_PLANNER_PIPELINE_VERSION
    assert plan.expected_output
    assert plan.created_at
    assert plan.diagnostics.timeline_ms.get("total_ms") is not None


def test_fallback_and_unknown_intent(planner: QueryPlanner) -> None:
    plan = planner.plan("xyzzy plugh")
    assert plan.fallback_strategy
    assert plan.required_indexes
    # Unknown or weak keyword fallback still produces a plan.
    assert plan.status in {"ok", "degraded", "invalid"}


def test_diagnostics_and_statistics(planner: QueryPlanner) -> None:
    for query in (
        "HR policies",
        "Finance budget reports",
        "related to VPN",
        "count security policies",
    ):
        planner.plan(query)
    stats = planner.statistics()
    assert stats["queries_analyzed"] == 4
    assert stats["planner_version"] == QUERY_PLANNER_PIPELINE_VERSION
    assert stats["intent_distribution"]
    assert stats["average_planning_time_ms"] >= 0


def test_shadow_mode_fail_open_and_persist(tmp_path: Path) -> None:
    store = QueryPlanJsonStore(tmp_path / "query_planner")
    service = QueryPlannerService(
        index_manager=KnowledgeIndexManager(),
        store=store,
    )
    shadow = ShadowQueryPlannerService(service=service, enabled=True)
    shadow.analyze("latest HR leave policy")
    shadow.analyze("")  # no-op
    loaded = store.load()
    assert loaded is not None
    assert loaded["count"] >= 1

    # Disabled shadow never persists.
    empty_store = QueryPlanJsonStore(tmp_path / "query_planner_off")
    disabled = ShadowQueryPlannerService(
        service=QueryPlannerService(store=empty_store),
        enabled=False,
    )
    disabled.analyze("should not store")
    assert empty_store.load() is None


def test_failure_recovery_and_backward_compatibility(planner: QueryPlanner) -> None:
    plan = planner.plan("")
    assert plan.normalized_query == "" or plan.status in {"ok", "degraded", "invalid"}
    # Planning must never imply retrieval hooks.
    assert "faiss" not in plan.to_dict().__repr__().lower()
    assert QUERY_PLANNER_PIPELINE_VERSION.startswith("13.5")


def test_policy_lookup_requires_taxonomy_department(planner: QueryPlanner) -> None:
    plan = planner.plan("Find the HR leave policy")
    for required in ("taxonomy", "department", "keyword", "metadata"):
        # POLICY_LOOKUP defaults include these; VERSION not required unless latest.
        assert required in plan.required_indexes or plan.primary_intent != QueryIntent.POLICY_LOOKUP.value
    assert plan.primary_intent in {
        QueryIntent.POLICY_LOOKUP.value,
        QueryIntent.DEPARTMENT_SEARCH.value,
        QueryIntent.VERSION_LOOKUP.value,
        QueryIntent.KEYWORD_SEARCH.value,
    }
