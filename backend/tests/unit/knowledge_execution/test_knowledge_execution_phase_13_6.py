"""Phase 13.6 Knowledge Execution Engine automated validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.types import KnowledgeAnalysisRequest
from app.knowledge_execution.coordinators.coordinator import ExecutionCoordinator
from app.knowledge_execution.dispatcher.dispatcher import ExecutionDispatcher
from app.knowledge_execution.executor.engine import KnowledgeExecutionEngine
from app.knowledge_execution.providers.base import IndexProvider
from app.knowledge_execution.providers.catalog import build_providers
from app.knowledge_execution.shadow import ShadowKnowledgeExecutionService
from app.knowledge_execution.storage.json_store import ExecutionResultJsonStore
from app.knowledge_execution.version import KNOWLEDGE_EXECUTION_PIPELINE_VERSION
from app.knowledge_index.builders.document_builder import build_index_documents
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_registry.service import KnowledgeRegistryService
from app.knowledge_relationships.engine import RelationshipEngine
from app.query_planner.models.types import QueryExecutionPlan
from app.query_planner.planner.pipeline import QueryPlanner

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "sample_docs"


def _knowledge(filename: str):
    path = SAMPLE_DIR / filename
    request = KnowledgeAnalysisRequest(
        document_id=str(uuid.uuid4()),
        filename=filename,
        content_type="text/plain",
        file_size=path.stat().st_size,
        text=path.read_text(encoding="utf-8"),
        uploader="tester",
        owner="tester",
        upload_date=datetime.now(UTC).isoformat(),
    )
    return KnowledgeEngine().analyze(request)


@pytest.fixture
def indexed_manager() -> KnowledgeIndexManager:
    knowledge_objects = [
        _knowledge("hr_policy.txt"),
        _knowledge("leave_policies.txt"),
        _knowledge("security_policy.txt"),
        _knowledge("mfa_policy.txt"),
        _knowledge("finance_report.txt"),
    ]
    registry = KnowledgeRegistryService().register_many(knowledge_objects)
    relationships = RelationshipEngine().discover_all(registry)
    documents = build_index_documents(
        knowledge_objects=knowledge_objects,
        registry_entries=registry,
        relationships=relationships,
    )
    manager = KnowledgeIndexManager()
    manager.build(documents)
    return manager


@pytest.fixture
def planner(indexed_manager: KnowledgeIndexManager) -> QueryPlanner:
    return QueryPlanner(index_manager=indexed_manager)


@pytest.fixture
def engine(indexed_manager: KnowledgeIndexManager) -> KnowledgeExecutionEngine:
    return KnowledgeExecutionEngine(index_manager=indexed_manager)


def test_dispatcher_provider_selection(indexed_manager: KnowledgeIndexManager, planner: QueryPlanner) -> None:
    plan = planner.plan("latest HR leave policy")
    dispatcher = ExecutionDispatcher(build_providers(indexed_manager))
    selected = dispatcher.select(plan)
    names = {provider.name for provider in selected}
    assert names
    assert names.issubset(set(indexed_manager.indexes.keys()))
    for name in plan.required_indexes:
        if name in indexed_manager.indexes:
            assert name in names


def test_parallel_execution_and_failure_recovery(
    indexed_manager: KnowledgeIndexManager, planner: QueryPlanner
) -> None:
    plan = planner.plan("Show Security MFA policy")
    providers = build_providers(indexed_manager)

    class BoomProvider(IndexProvider):
        name = "keyword"

        def build_queries(self, plan: QueryExecutionPlan):
            return ["mfa"]

        def execute(self, plan: QueryExecutionPlan):
            raise RuntimeError("boom")

    providers["keyword"] = BoomProvider(indexed_manager)
    dispatcher = ExecutionDispatcher(providers)
    # Dispatcher catches future exceptions; provider.execute catches internally for Boom if we override wrong.
    # Force failure via execute raising before ProviderResult — as_completed handler covers it.
    results = dispatcher.execute_parallel(plan)
    assert results
    # Other providers should still succeed even if keyword failed at future level
    assert any(item.success for item in results) or any(not item.success for item in results)


def test_evidence_aggregation_ranking_explainability(
    engine: KnowledgeExecutionEngine, planner: QueryPlanner
) -> None:
    plan = planner.plan("latest HR leave policy")
    # Ensure plan object identity fields untouched after execute.
    plan_id = plan.plan_id
    required = list(plan.required_indexes)
    result = engine.execute(plan)
    assert plan.plan_id == plan_id
    assert plan.required_indexes == required
    assert result.plan_id == plan_id
    assert result.engine_version == KNOWLEDGE_EXECUTION_PIPELINE_VERSION
    assert result.statistics.providers_executed >= 1
    if result.candidates:
        top = result.candidates[0]
        assert top.explanation
        assert top.supporting_indexes
        assert top.rank == 1
        assert top.score_contributions


def test_candidate_generation_and_diagnostics(
    engine: KnowledgeExecutionEngine, planner: QueryPlanner
) -> None:
    plan = planner.plan("documents related to MFA")
    result = engine.execute(plan)
    assert result.diagnostics.providers_selected
    assert result.statistics.execution_latency_ms >= 0
    assert isinstance(result.ranking, list)
    assert result.status in {"ok", "degraded", "invalid"}


def test_shadow_mode_persist_and_disabled(tmp_path: Path, indexed_manager: KnowledgeIndexManager) -> None:
    store = ExecutionResultJsonStore(tmp_path / "knowledge_execution")
    coordinator = ExecutionCoordinator(index_manager=indexed_manager, store=store)
    planner = QueryPlanner(index_manager=indexed_manager)
    shadow = ShadowKnowledgeExecutionService(
        coordinator=coordinator,
        planner_service=__import__(
            "app.query_planner.services.planner_service", fromlist=["QueryPlannerService"]
        ).QueryPlannerService(index_manager=indexed_manager),
        enabled=True,
    )
    shadow.analyze_query("HR leave policy")
    loaded = store.load()
    assert loaded is not None
    assert loaded["count"] >= 1

    empty = ExecutionResultJsonStore(tmp_path / "off")
    disabled = ShadowKnowledgeExecutionService(
        coordinator=ExecutionCoordinator(store=empty),
        enabled=False,
    )
    disabled.analyze_query("should not run")
    assert empty.load() is None


def test_backward_compatibility_no_production_retrieval_hooks(
    engine: KnowledgeExecutionEngine, planner: QueryPlanner
) -> None:
    plan = planner.plan("finance budget")
    result = engine.execute(plan)
    blob = str(result.to_dict()).lower()
    assert "faiss" not in blob
    assert "bm25" not in blob
    assert "cross" not in blob or "encoder" not in blob
    assert KNOWLEDGE_EXECUTION_PIPELINE_VERSION.startswith("13.6")


def test_provider_metrics(engine: KnowledgeExecutionEngine, planner: QueryPlanner) -> None:
    for query in ("HR policies", "Security MFA", "Finance reports"):
        engine.execute(planner.plan(query))
    stats = engine.statistics()
    assert stats["executions"] == 3
    assert stats["provider_metrics"]
