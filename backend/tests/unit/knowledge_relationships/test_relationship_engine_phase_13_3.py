"""Phase 13.3 Relationship Engine automated validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Document, DocumentKnowledgeRecord, Role, User  # noqa: F401
from app.db.models.knowledge_registry import KnowledgeRegistryEntry  # noqa: F401
from app.db.models.knowledge_relationship import KnowledgeRelationship, RelationshipEvidence  # noqa: F401
from app.documents.status import DocumentStatus
from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.types import KnowledgeAnalysisRequest
from app.knowledge_registry.repository import KnowledgeRegistryRepository
from app.knowledge_registry.service import KnowledgeRegistryService
from app.knowledge_relationships.engine import RelationshipEngine
from app.knowledge_relationships.enums import RelationshipType
from app.knowledge_relationships.repository import RelationshipRepository
from app.knowledge_relationships.statistics import build_relationship_statistics
from tests.constants import TEST_PASSWORD_HASH

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "sample_docs"
_VALID_TYPES = {item.value for item in RelationshipType}


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def uploader(db_session: Session) -> User:
    role = Role(name="Admin", description="Administrator")
    user = User(
        email="rel@example.com",
        username="rel",
        full_name="Rel Tester",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    return user


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


def _registry_batch():
    service = KnowledgeRegistryService()
    objects = [
        _knowledge("hr_policy.txt"),
        _knowledge("leave_policies.txt"),
        _knowledge("employee_handbook.txt"),
        _knowledge("security_policy.txt"),
        _knowledge("leave_policies.txt", override_name="LeavePolicy_v2.pdf"),
        _knowledge("leave_policies.txt", override_name="LeavePolicy_Final.pdf"),
    ]
    return service.register_many(objects)


def test_relationships_have_valid_ids_types_evidence_confidence() -> None:
    entries = _registry_batch()
    relationships = RelationshipEngine().discover_all(entries)

    assert relationships
    for rel in relationships:
        assert rel.source_knowledge_id
        assert rel.target_knowledge_id
        assert rel.source_knowledge_id != rel.target_knowledge_id
        assert rel.relationship_type in _VALID_TYPES
        assert rel.evidence
        assert rel.evidence_source
        assert 0.0 <= rel.confidence <= 1.0
        assert rel.confidence_kind == "heuristic_estimate"


def test_no_self_links() -> None:
    entries = _registry_batch()
    relationships = RelationshipEngine().discover_all(entries)
    assert all(rel.source_knowledge_id != rel.target_knowledge_id for rel in relationships)


def test_version_and_duplicate_relationships_exist() -> None:
    entries = _registry_batch()
    relationships = RelationshipEngine().discover_all(entries)
    types = {rel.relationship_type for rel in relationships}
    assert RelationshipType.NEXT_VERSION.value in types or RelationshipType.PREVIOUS_VERSION.value in types
    assert RelationshipType.DUPLICATE_OF.value in types or RelationshipType.SUPERSEDES.value in types
    assert RelationshipType.SAME_COLLECTION.value in types


def test_relationship_statistics_coverage() -> None:
    entries = _registry_batch()
    relationships = RelationshipEngine().discover_all(entries)
    stats = build_relationship_statistics(relationships, entries)
    assert stats.relationship_count == len(relationships)
    assert stats.coverage > 0
    assert stats.avg_confidence > 0
    assert stats.type_counts


def test_relationship_repository_persists(
    db_session: Session,
    uploader: User,
) -> None:
    entries = _registry_batch()
    # Persist registry rows so FK targets exist.
    registry_repo = KnowledgeRegistryRepository(db_session)
    registry_repo.ensure_seed_data()
    for entry in entries:
        document_id = uuid.UUID(entry.document_id)
        db_session.add(
            Document(
                id=document_id,
                filename=entry.filename,
                content_type="text/plain",
                file_size=100,
                checksum=f"checksum-{document_id}",
                storage_path=f"{document_id}.txt",
                uploaded_by=uploader.id,
                owner_id=uploader.id,
                status=DocumentStatus.SEARCHABLE.value,
                tenant_id="default",
            )
        )
    db_session.commit()
    for entry in entries:
        registry_repo.upsert_entry(entry)

    engine = RelationshipEngine()
    source = entries[0]
    peers = entries[1:]
    rels = engine.discover_for(source, peers)
    saved = RelationshipRepository(db_session).replace_for_source(source.knowledge_id, rels)
    assert len(saved) == len(rels)
    assert db_session.query(KnowledgeRelationship).count() == len(rels)
    assert db_session.query(RelationshipEvidence).count() >= len(rels)


def test_shadow_mode_isolation_uses_registry_only() -> None:
    """Discovery operates on RegistryEntry objects — no vector store dependency."""
    entries = _registry_batch()
    engine = RelationshipEngine()
    rels = engine.discover_all(entries)
    assert isinstance(rels, list)
    # Engine does not require document_knowledge / FAISS.
    assert all(rel.created_by == "relationship_engine" for rel in rels)
