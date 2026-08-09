"""Phase 13.8 Worker Orchestration automated validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.types import KnowledgeAnalysisRequest
from app.knowledge_index.builders.document_builder import build_index_documents
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_orchestration.orchestrator.orchestrator import KnowledgeOrchestrator
from app.knowledge_orchestration.registry.worker_registry import WorkerRegistry
from app.knowledge_orchestration.scheduler.scheduler import WorkerScheduler
from app.knowledge_orchestration.shadow import ShadowKnowledgeOrchestrationService
from app.knowledge_orchestration.storage.json_store import OrchestrationJsonStore
from app.knowledge_orchestration.version import KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION
from app.knowledge_orchestration.workers.base import Worker
from app.knowledge_orchestration.models.types import WorkerCapability, WorkerEvidence
from app.knowledge_registry.service import KnowledgeRegistryService
from app.knowledge_relationships.engine import RelationshipEngine
from app.query_planner.models.types import QueryExecutionPlan
from app.query_planner.planner.pipeline import QueryPlanner
from app.query_planner.services.planner_service import QueryPlannerService

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
        _knowledge("mfa_policy.txt"),
        _knowledge("finance_report.txt"),
    ]
    registry = KnowledgeRegistryService().register_many(knowledge_objects)
    relationships = RelationshipEngine().discover_all(registry)
    docs = build_index_documents(
        knowledge_objects=knowledge_objects,
        registry_entries=registry,
        relationships=relationships,
    )
    manager = KnowledgeIndexManager()
    manager.build(docs)
    return manager


@pytest.fixture
def orchestrator(indexed_manager: KnowledgeIndexManager) -> KnowledgeOrchestrator:
    registry = WorkerRegistry.with_defaults(index_manager=indexed_manager)
    return KnowledgeOrchestrator(registry=registry, index_manager=indexed_manager)


def test_worker_discovery_and_registration(indexed_manager: KnowledgeIndexManager) -> None:
    registry = WorkerRegistry.with_defaults(index_manager=indexed_manager)
    ids = {worker.id() for worker in registry.list_workers()}
    for expected in (
        "metadata",
        "collection",
        "department",
        "taxonomy",
        "entity",
        "keyword",
        "topic",
        "tag",
        "relationship",
        "version",
        "graph",
    ):
        assert expected in ids
    assert registry.discover()
    assert registry.metadata()
    assert registry.health()


def test_scheduling_dependency_and_parallel(indexed_manager: KnowledgeIndexManager) -> None:
    registry = WorkerRegistry.with_defaults(index_manager=indexed_manager)
    workers = registry.list_workers()
    schedule = WorkerScheduler().build_schedule(workers)
    assert schedule.groups
    # Graph depends on others — should not be alone in the first group unless only one worker.
    flat = [worker_id for group in schedule.groups for worker_id in group]
    assert "graph" in flat
    if len(schedule.groups) > 1:
        assert "graph" not in schedule.groups[0] or len(schedule.groups[0]) == 1


def test_orchestrate_merge_and_diagnostics(
    orchestrator: KnowledgeOrchestrator, indexed_manager: KnowledgeIndexManager
) -> None:
    plan = QueryPlanner(index_manager=indexed_manager).plan("latest HR leave policy")
    result = orchestrator.orchestrate(plan)
    assert result.orchestrator_version == KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION
    assert result.diagnostics.eligible_workers
    assert result.diagnostics.timeline
    assert result.diagnostics.merger
    assert "candidates" in result.candidate_evidence_set


def test_failure_recovery_timeout_handling(indexed_manager: KnowledgeIndexManager) -> None:
    class BoomWorker(Worker):
        def id(self) -> str:
            return "boom"

        def capabilities(self):
            return [WorkerCapability(name="test:boom")]

        def supports(self, plan: QueryExecutionPlan) -> bool:
            return True

        def execute(self, plan: QueryExecutionPlan, *, context=None) -> WorkerEvidence:
            raise RuntimeError("boom")

        def priority(self) -> int:
            return 1

    class SlowWorker(Worker):
        def id(self) -> str:
            return "slow"

        def capabilities(self):
            return [WorkerCapability(name="test:slow")]

        def supports(self, plan: QueryExecutionPlan) -> bool:
            return True

        def execute(self, plan: QueryExecutionPlan, *, context=None) -> WorkerEvidence:
            import time

            time.sleep(0.2)
            return WorkerEvidence(worker_id="slow", success=True)

        def priority(self) -> int:
            return 1

    registry = WorkerRegistry.with_defaults(index_manager=indexed_manager)
    registry.register(BoomWorker())
    registry.register(SlowWorker())
    scheduler = WorkerScheduler(default_timeout_ms=50.0, budget_ms=5000.0)
    orch = KnowledgeOrchestrator(
        registry=registry,
        scheduler=scheduler,
        index_manager=indexed_manager,
    )
    plan = QueryPlanner(index_manager=indexed_manager).plan("HR policies")
    result = orch.orchestrate(plan)
    assert "boom" in result.diagnostics.failed_workers or any(
        item.worker_id == "boom" and not item.success for item in result.worker_evidence
    )
    assert "slow" in result.diagnostics.timed_out_workers or any(
        item.worker_id == "slow" and item.timed_out for item in result.worker_evidence
    )
    # Other workers still ran / orchestration did not raise
    assert result.status in {"ok", "degraded", "empty", "invalid"}


def test_shadow_mode_and_backward_compatibility(
    tmp_path: Path, indexed_manager: KnowledgeIndexManager
) -> None:
    store_path = tmp_path / "knowledge_orchestration"
    registry = WorkerRegistry.with_defaults(index_manager=indexed_manager)
    orch = KnowledgeOrchestrator(registry=registry, index_manager=indexed_manager)
    shadow = ShadowKnowledgeOrchestrationService(
        orchestrator=orch,
        planner=QueryPlannerService(index_manager=indexed_manager),
        enabled=True,
    )
    shadow._store = OrchestrationJsonStore(store_path)  # noqa: SLF001
    shadow.analyze_query("Security MFA policy")
    loaded = shadow._store.load()
    assert loaded is not None
    assert loaded["count"] >= 1

    disabled = ShadowKnowledgeOrchestrationService(enabled=False)
    disabled.analyze_query("no-op")
    assert KNOWLEDGE_ORCHESTRATION_PIPELINE_VERSION.startswith("13.8")
