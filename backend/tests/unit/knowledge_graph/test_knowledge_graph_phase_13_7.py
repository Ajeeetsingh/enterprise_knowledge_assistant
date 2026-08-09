"""Phase 13.7 Knowledge Graph automated validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.types import KnowledgeAnalysisRequest
from app.knowledge_execution.executor.engine import KnowledgeExecutionEngine
from app.knowledge_graph.models.enums import EdgeType, NodeType
from app.knowledge_graph.providers.bridge import GraphAwareExecutionBridge
from app.knowledge_graph.providers.graph_provider import GraphProvider
from app.knowledge_graph.services.graph_service import KnowledgeGraphService
from app.knowledge_graph.shadow import ShadowKnowledgeGraphService
from app.knowledge_graph.version import KNOWLEDGE_GRAPH_PIPELINE_VERSION
from app.knowledge_index.builders.document_builder import build_index_documents
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_registry.service import KnowledgeRegistryService
from app.knowledge_relationships.engine import RelationshipEngine
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
def graph_bundle():
    knowledge_objects = [
        _knowledge("hr_policy.txt"),
        _knowledge("leave_policies.txt"),
        _knowledge("security_policy.txt"),
        _knowledge("mfa_policy.txt"),
        _knowledge("finance_report.txt"),
    ]
    registry = KnowledgeRegistryService().register_many(knowledge_objects)
    relationships = RelationshipEngine().discover_all(registry)
    index_docs = build_index_documents(
        knowledge_objects=knowledge_objects,
        registry_entries=registry,
        relationships=relationships,
    )
    manager = KnowledgeIndexManager()
    manager.build(index_docs)
    service = KnowledgeGraphService()
    stats = service.rebuild(
        registry_entries=registry,
        relationships=relationships,
        index_documents=index_docs,
    )
    return service, registry, relationships, index_docs, manager, stats


def test_graph_construction(graph_bundle) -> None:
    service, registry, _, _, _, stats = graph_bundle
    assert stats["node_count"] > 0
    assert stats["edge_count"] > 0
    assert stats["graph_version"] == KNOWLEDGE_GRAPH_PIPELINE_VERSION
    assert any(node.type == NodeType.KNOWLEDGE_OBJECT.value for node in service.graph.nodes())
    assert any(edge.type in {item.value for item in EdgeType} for edge in service.graph.edges())
    assert len(registry) >= 1


def test_incremental_update(graph_bundle) -> None:
    service, registry, relationships, index_docs, _, _ = graph_bundle
    before = service.statistics()["node_count"]
    service.upsert(registry[0], index_document=index_docs[0], relationships=relationships[:1])
    after = service.statistics()["node_count"]
    assert after >= before


def test_traversal_filtering_cycle_and_budget(graph_bundle) -> None:
    service, registry, _, _, _, _ = graph_bundle
    root = service.knowledge_object_node_id(registry[0].knowledge_id)
    result = service.traverse(root, max_depth=2, budget=20, direction="both")
    assert root in result.visited_nodes
    assert result.elapsed_ms >= 0
    assert result.diagnostics["max_depth"] == 2
    # Depth-limited: no step deeper than 2
    assert all(step.depth <= 2 for step in result.steps)


def test_weighted_traversal_and_expansion(graph_bundle) -> None:
    service, registry, _, _, _, _ = graph_bundle
    root = service.knowledge_object_node_id(registry[0].knowledge_id)
    neighbors = service.find_neighbors(root)
    assert isinstance(neighbors, list)
    related = service.find_related(root, max_depth=2)
    assert related.seed_node_ids == [root]
    entities = service.find_entities(root)
    assert entities.elapsed_ms >= 0
    versions = service.find_versions(root)
    assert isinstance(versions.items, list)


def test_graph_scoring_and_diagnostics(graph_bundle) -> None:
    service, registry, _, _, _, _ = graph_bundle
    root = service.knowledge_object_node_id(registry[0].knowledge_id)
    evidence = service.expand_node(root, mode="neighbors", max_depth=1)
    if evidence.items:
        assert evidence.items[0].score >= 0
        assert evidence.items[0].explanation
    diagnostics = service.diagnostics()
    assert "health" in diagnostics
    assert "statistics" in diagnostics


def test_provider_integration_and_unavailable(graph_bundle) -> None:
    service, registry, _, _, manager, _ = graph_bundle
    planner = QueryPlanner(index_manager=manager)
    engine = KnowledgeExecutionEngine(index_manager=manager)
    provider = GraphProvider(service)
    bridge = GraphAwareExecutionBridge(execution_engine=engine, graph_provider=provider)
    plan = planner.plan("documents related to MFA")
    payload = bridge.execute(plan)
    assert "candidate_evidence_set" in payload
    assert "graph_expansion" in payload

    empty = GraphProvider(KnowledgeGraphService())
    assert empty.available is False
    soft = empty.expand_candidates(plan, engine.execute(plan))
    assert "graph_unavailable" in soft.warnings


def test_shadow_mode_disabled_and_backward_compatibility() -> None:
    shadow = ShadowKnowledgeGraphService(enabled=False)
    assert shadow.rebuild_from_persistence() == 0
    shadow.analyze_query("hr leave")
    assert KNOWLEDGE_GRAPH_PIPELINE_VERSION.startswith("13.7")
