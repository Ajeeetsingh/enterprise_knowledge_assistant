"""Phase 13.2 Knowledge Registry automated validation."""

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
from app.documents.status import DocumentStatus
from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.types import KnowledgeAnalysisRequest
from app.knowledge_registry.aliases.normalizer import AliasNormalizer
from app.knowledge_registry.repository import KnowledgeRegistryRepository
from app.knowledge_registry.service import KnowledgeRegistryService
from app.knowledge_registry.version import REGISTRY_PIPELINE_VERSION
from tests.constants import TEST_PASSWORD_HASH

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "sample_docs"


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
        email="registry@example.com",
        username="registry",
        full_name="Registry Tester",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    return user


def _knowledge_from_sample(filename: str, *, override_name: str | None = None):
    path = SAMPLE_DIR / filename
    text = path.read_text(encoding="utf-8")
    request = KnowledgeAnalysisRequest(
        document_id=str(uuid.uuid4()),
        filename=override_name or filename,
        content_type="text/plain",
        file_size=path.stat().st_size,
        text=text,
        uploader="tester",
        owner="tester",
        upload_date=datetime.now(UTC).isoformat(),
    )
    return KnowledgeEngine().analyze(request)


def test_every_sample_knowledge_object_is_registered() -> None:
    service = KnowledgeRegistryService()
    files = sorted(SAMPLE_DIR.glob("*.txt"))
    knowledge_objects = [_knowledge_from_sample(path.name) for path in files]
    entries = service.register_many(knowledge_objects)

    assert len(entries) == len(knowledge_objects)
    assert all(entry.knowledge_id for entry in entries)
    assert all(entry.collections for entry in entries)
    stats = service.statistics(entries)
    assert stats.registered_count == len(entries)
    assert stats.coverage_with_collection == 1.0


def test_collections_and_taxonomy_generation() -> None:
    hr = _knowledge_from_sample("hr_policy.txt")
    finance = _knowledge_from_sample("finance_report.txt")
    security = _knowledge_from_sample("incident_response.txt")
    service = KnowledgeRegistryService()
    entries = service.register_many([hr, finance, security])

    by_name = {entry.filename: entry for entry in entries}
    assert "hr" in by_name["hr_policy.txt"].collections
    assert by_name["hr_policy.txt"].taxonomy_path.startswith("HR/")
    assert "finance" in by_name["finance_report.txt"].collections
    assert "Reports" in by_name["finance_report.txt"].taxonomy_path
    assert "security" in by_name["incident_response.txt"].collections
    assert "Security/" in by_name["incident_response.txt"].taxonomy_path


def test_canonical_alias_normalization() -> None:
    normalizer = AliasNormalizer()
    assert normalizer.normalize_term("vacation") == "Annual Leave"
    assert normalizer.normalize_term("Paid Leave") == "Annual Leave"
    assert normalizer.normalize_term("Virtual Private Network") == "VPN"
    assert normalizer.normalize_term("corporate vpn") == "VPN"

    knowledge = _knowledge_from_sample("leave_policies.txt")
    canons, applied = normalizer.normalize_knowledge(knowledge)
    assert "Annual Leave" in canons
    assert any(item["canonical"] == "Annual Leave" for item in applied)


def test_version_and_duplicate_detection() -> None:
    service = KnowledgeRegistryService()
    v1 = _knowledge_from_sample("leave_policies.txt", override_name="LeavePolicy.pdf")
    v2 = _knowledge_from_sample("leave_policies.txt", override_name="LeavePolicy_v2.pdf")
    final = _knowledge_from_sample("leave_policies.txt", override_name="LeavePolicy_Final.pdf")
    entries = service.register_many([v1, v2, final])

    keys = {entry.version_group_key for entry in entries}
    assert len(keys) == 1
    labels = {entry.version_label for entry in entries}
    assert "v2" in labels or "final" in labels
    # At least one should be marked as a probable duplicate/version peer.
    assert any(entry.probable_duplicate_of for entry in entries)


def test_knowledge_health_is_generated() -> None:
    service = KnowledgeRegistryService()
    knowledge = _knowledge_from_sample("mfa_policy.txt")
    draft = _knowledge_from_sample("password_policy.txt", override_name="password_policy_draft.txt")
    entries = service.register_many([knowledge, draft])
    healths = {entry.filename: entry.health for entry in entries}
    assert healths["mfa_policy.txt"] in {"Verified", "Healthy", "Incomplete", "Duplicate"}
    assert healths["password_policy_draft.txt"] == "Draft"
    assert all(entry.health for entry in entries)


def test_registry_repository_persists_entry(
    db_session: Session,
    uploader: User,
) -> None:
    knowledge = _knowledge_from_sample("hr_policy.txt")
    document_id = uuid.UUID(knowledge.document_id)
    db_session.add(
        Document(
            id=document_id,
            filename=knowledge.metadata.filename,
            content_type="text/plain",
            file_size=knowledge.metadata.file_size,
            checksum="reg-checksum",
            storage_path=f"{document_id}.txt",
            uploaded_by=uploader.id,
            owner_id=uploader.id,
            status=DocumentStatus.SEARCHABLE.value,
            tenant_id="default",
        )
    )
    db_session.commit()

    service = KnowledgeRegistryService()
    entry = service.register_many([knowledge])[0]
    repo = KnowledgeRegistryRepository(db_session)
    repo.ensure_seed_data()
    record = repo.upsert_entry(entry)

    assert record.id is not None
    assert record.pipeline_version == REGISTRY_PIPELINE_VERSION
    assert record.primary_collection == "hr"
    assert repo.get_by_document_id(document_id) is not None


def test_registry_backward_compatible_with_knowledge_engine() -> None:
    """Registry organization must not mutate Knowledge Object core fields."""
    knowledge = _knowledge_from_sample("mfa_policy.txt")
    before = knowledge.to_dict()
    KnowledgeRegistryService().register_many([knowledge])
    after = knowledge.to_dict()
    assert before == after
