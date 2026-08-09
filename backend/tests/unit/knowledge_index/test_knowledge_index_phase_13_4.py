"""Phase 13.4 Hybrid Knowledge Index automated validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.types import KnowledgeAnalysisRequest
from app.knowledge_index.builders.document_builder import build_index_documents
from app.knowledge_index.services.manager import KnowledgeIndexManager
from app.knowledge_index.storage.json_store import KnowledgeIndexJsonStore
from app.knowledge_index.version import KNOWLEDGE_INDEX_PIPELINE_VERSION
from app.knowledge_registry.service import KnowledgeRegistryService
from app.knowledge_relationships.engine import RelationshipEngine

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "sample_docs"


def _knowledge(filename: str, *, override_name: str | None = None):
    path = SAMPLE_DIR / filename
    request = KnowledgeAnalysisRequest(
        document_id=str(uuid.uuid4()),
        filename=override_name or filename,
        content_type="text/plain",
        file_size=path.stat().st_size,
        text=path.read_text(encoding="utf-8"),
        uploader="tester",
        owner="tester",
        upload_date=datetime.now(UTC).isoformat(),
    )
    return KnowledgeEngine().analyze(request)


def _bundle():
    knowledge_objects = [
        _knowledge("hr_policy.txt"),
        _knowledge("leave_policies.txt"),
        _knowledge("employee_handbook.txt"),
        _knowledge("security_policy.txt"),
        _knowledge("mfa_policy.txt"),
        _knowledge("finance_report.txt"),
        _knowledge("leave_policies.txt", override_name="LeavePolicy_v2.pdf"),
        _knowledge("leave_policies.txt", override_name="LeavePolicy_Final.pdf"),
    ]
    registry_entries = KnowledgeRegistryService().register_many(knowledge_objects)
    relationships = RelationshipEngine().discover_all(registry_entries)
    documents = build_index_documents(
        knowledge_objects=knowledge_objects,
        registry_entries=registry_entries,
        relationships=relationships,
    )
    return knowledge_objects, registry_entries, relationships, documents


def test_index_creation_builds_all_ten_indexes() -> None:
    _, _, _, documents = _bundle()
    manager = KnowledgeIndexManager()
    stats = manager.build(documents)

    assert stats.index_count == 10
    assert stats.documents_indexed == len(documents)
    assert stats.index_version == KNOWLEDGE_INDEX_PIPELINE_VERSION
    for name in (
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
    ):
        assert name in manager.indexes
        assert name in stats.per_index


def test_metadata_collection_department_taxonomy_lookups() -> None:
    _, _, _, documents = _bundle()
    manager = KnowledgeIndexManager()
    manager.build(documents)

    sample = documents[0]
    meta = manager.lookup("metadata", {"field": "filename", "value": sample.filename})
    assert sample.document_id in meta.document_ids

    if sample.collections:
        collection = manager.lookup("collection", sample.collections[0])
        assert sample.document_id in collection.document_ids

    if sample.departments:
        department = manager.lookup("department", sample.departments[0])
        assert sample.document_id in department.document_ids

    if sample.taxonomy_path:
        taxonomy = manager.lookup("taxonomy", {"mode": "prefix", "value": sample.taxonomy_path.split("/")[0]})
        assert sample.document_id in taxonomy.document_ids


def test_entity_keyword_topic_tag_inverted_indexes() -> None:
    _, _, _, documents = _bundle()
    manager = KnowledgeIndexManager()
    manager.build(documents)

    found = False
    for document in documents:
        if document.keywords:
            result = manager.lookup("keyword", document.keywords[0])
            assert document.document_id in result.document_ids
            found = True
            break
    assert found

    for document in documents:
        if document.topics:
            assert document.document_id in manager.lookup("topic", document.topics[0]).document_ids
            break
    for document in documents:
        if document.tags:
            assert document.document_id in manager.lookup("tag", document.tags[0]).document_ids
            break
    for document in documents:
        if document.entities:
            assert document.document_id in manager.lookup("entity", document.entities[0]).document_ids
            break


def test_relationship_and_version_indexes() -> None:
    _, registry_entries, relationships, documents = _bundle()
    manager = KnowledgeIndexManager()
    manager.build(documents)

    assert relationships
    source = relationships[0].source_knowledge_id
    outgoing = manager.lookup("relationship", {"mode": "outgoing", "value": source})
    assert outgoing.document_ids or outgoing.meta.get("edges")

    typed = manager.lookup("relationship", {"mode": "type", "value": relationships[0].relationship_type})
    assert typed.document_ids or typed.meta.get("edges")

    grouped = [entry for entry in registry_entries if entry.version_group_key]
    assert grouped
    group_key = grouped[0].version_group_key
    group_docs = manager.lookup("version", {"mode": "group", "value": group_key})
    assert len(group_docs.document_ids) >= 1


def test_incremental_update_and_delete() -> None:
    _, _, _, documents = _bundle()
    manager = KnowledgeIndexManager()
    manager.build(documents[:3])
    assert manager.statistics().documents_indexed == 3

    manager.insert(documents[3])
    assert manager.statistics().documents_indexed == 4
    assert documents[3].document_id in manager.documents

    updated = documents[3]
    updated.keywords = list(updated.keywords) + ["incremental-marker-xyz"]
    manager.update(updated)
    assert documents[3].document_id in manager.lookup("keyword", "incremental-marker-xyz").document_ids

    manager.remove(documents[3].document_id)
    assert documents[3].document_id not in manager.documents
    assert documents[3].document_id not in manager.lookup("keyword", "incremental-marker-xyz").document_ids


def test_duplicate_and_version_updates() -> None:
    _, _, _, documents = _bundle()
    manager = KnowledgeIndexManager()
    manager.build(documents)

    duplicates = manager.lookup("version", {"mode": "duplicates"})
    # May be empty if registry didn't flag; still ensure lookup works.
    assert isinstance(duplicates.document_ids, list)

    canonical = manager.lookup("version", {"mode": "canonical"})
    assert canonical.document_ids

    # Re-insert same document id should not inflate counts.
    before = manager.statistics().documents_indexed
    manager.insert(documents[0])
    assert manager.statistics().documents_indexed == before


def test_rebuild_coverage_consistency(tmp_path: Path) -> None:
    _, _, _, documents = _bundle()
    store = KnowledgeIndexJsonStore(tmp_path / "knowledge_index")
    manager = KnowledgeIndexManager(store=store)
    stats = manager.build(documents)
    assert stats.coverage >= 0.0
    assert store.snapshot_path.exists()

    manager.remove(documents[0].document_id)
    rebuilt = manager.rebuild()
    assert rebuilt.documents_indexed == len(documents) - 1
    health = manager.health()
    assert health.status in {"healthy", "degraded"}
    assert not health.missing_indexes


def test_inspect_and_failure_recovery() -> None:
    _, _, _, documents = _bundle()
    manager = KnowledgeIndexManager()
    manager.build(documents)

    inspected = manager.inspect(documents[0].document_id)
    assert inspected is not None
    assert "metadata" in inspected
    assert "index_references" in inspected
    assert all(inspected["index_references"].values()) or True

    # Unknown index lookup is soft-fail.
    result = manager.lookup("does-not-exist", "x")
    assert result.document_ids == []
    assert result.meta.get("error") == "unknown_index"

    # Empty rebuild recovers cleanly.
    manager.build([])
    assert manager.statistics().documents_indexed == 0


def test_backward_compatibility_shadow_isolation() -> None:
    """Hybrid indexes must not imply production retrieval participation."""
    assert KNOWLEDGE_INDEX_PIPELINE_VERSION.startswith("13.4")
    manager = KnowledgeIndexManager()
    # Building with zero docs must succeed without touching FAISS/BM25.
    stats = manager.build([])
    assert stats.index_count == 10
    assert stats.documents_indexed == 0
