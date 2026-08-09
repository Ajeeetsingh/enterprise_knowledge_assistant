"""Phase 13.1 Knowledge Engine automated validation."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Document, DocumentKnowledgeRecord, Role, User  # noqa: F401
from app.documents.events import DocumentUploaded
from app.documents.status import DocumentStatus
from app.knowledge_engine.engine import KnowledgeEngine
from app.knowledge_engine.enums import Department, DocumentType
from app.knowledge_engine.repository import KnowledgeRepository
from app.knowledge_engine.shadow import ShadowKnowledgeService
from app.knowledge_engine.types import KnowledgeAnalysisRequest
from app.knowledge_engine.version import PIPELINE_VERSION
from app.storage.local import LocalStorage
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
        email="kie@example.com",
        username="kie",
        full_name="KIE Tester",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles.append(role)
    db_session.add_all([role, user])
    db_session.commit()
    return user


def _request_from_sample(filename: str) -> KnowledgeAnalysisRequest:
    path = SAMPLE_DIR / filename
    text = path.read_text(encoding="utf-8")
    return KnowledgeAnalysisRequest(
        document_id=str(uuid.uuid4()),
        filename=filename,
        content_type="text/plain",
        file_size=path.stat().st_size,
        text=text,
        uploader="tester",
        owner="tester",
        upload_date=datetime.now(UTC).isoformat(),
    )


def test_hr_policy_knowledge_object_fields() -> None:
    engine = KnowledgeEngine()
    knowledge = engine.analyze(_request_from_sample("hr_policy.txt"))

    assert knowledge.summary.short
    assert knowledge.summary.detailed
    assert knowledge.document_type == DocumentType.POLICY.value
    assert Department.HR.value in knowledge.departments
    assert len(knowledge.keywords) >= 3
    assert knowledge.entities.total_count() >= 1
    assert "HR-POL-2025-001" in knowledge.entities.document_ids or any(
        "HR-POL" in item for item in knowledge.entities.document_ids
    )
    assert len(knowledge.tags) >= 2
    assert knowledge.metadata.filename == "hr_policy.txt"
    assert knowledge.metadata.extension == "txt"
    assert knowledge.metadata.file_size > 0
    assert knowledge.processing_info.pipeline_version == PIPELINE_VERSION
    assert knowledge.processing_info.model_used
    assert knowledge.processing_info.processing_time_ms >= 0
    assert knowledge.confidence.overall > 0


def test_handbook_and_finance_classification() -> None:
    engine = KnowledgeEngine()
    handbook = engine.analyze(_request_from_sample("employee_handbook.txt"))
    finance = engine.analyze(_request_from_sample("finance_report.txt"))

    assert handbook.document_type == DocumentType.HANDBOOK.value
    assert Department.HR.value in handbook.departments
    assert finance.document_type == DocumentType.FINANCIAL_REPORT.value
    assert Department.FINANCE.value in finance.departments


def test_security_samples_produce_entities_and_topics() -> None:
    engine = KnowledgeEngine()
    for filename in ("security_policy.txt", "mfa_policy.txt", "incident_response.txt"):
        knowledge = engine.analyze(_request_from_sample(filename))
        assert Department.SECURITY.value in knowledge.departments
        assert knowledge.topics
        assert knowledge.keywords
        assert knowledge.processing_info.status in {"success", "partial"}


@pytest.mark.parametrize(
    "filename",
    sorted(path.name for path in SAMPLE_DIR.glob("*.txt")),
)
def test_all_txt_samples_produce_complete_knowledge_objects(filename: str) -> None:
    knowledge = KnowledgeEngine().analyze(_request_from_sample(filename))
    assert knowledge.summary.short
    assert knowledge.summary.detailed
    assert knowledge.document_type
    assert knowledge.departments
    assert knowledge.keywords
    assert knowledge.tags
    assert knowledge.metadata.filename == filename
    assert knowledge.processing_info.pipeline_version == PIPELINE_VERSION
    payload = knowledge.to_dict()
    assert DocumentKnowledgeRecord  # imported for metadata create_all
    restored = type(knowledge).from_dict(payload)
    assert restored.document_id == knowledge.document_id
    assert restored.document_type == knowledge.document_type


def test_repository_upsert_persists_knowledge_object(
    db_session: Session,
    uploader: User,
) -> None:
    document_id = uuid.uuid4()
    db_session.add(
        Document(
            id=document_id,
            filename="hr_policy.txt",
            content_type="text/plain",
            file_size=100,
            checksum="abc",
            storage_path=f"{document_id}.txt",
            uploaded_by=uploader.id,
            owner_id=uploader.id,
            status=DocumentStatus.SEARCHABLE.value,
            tenant_id="default",
        )
    )
    db_session.commit()

    knowledge = KnowledgeEngine().analyze(_request_from_sample("hr_policy.txt"))
    knowledge.document_id = str(document_id)
    record = KnowledgeRepository(db_session).upsert(knowledge)

    assert record.document_id == document_id
    assert record.document_type == knowledge.document_type
    assert json.loads(record.knowledge_json)["document_id"] == str(document_id)
    again = KnowledgeRepository(db_session).get_by_document_id(document_id)
    assert again is not None
    assert again.short_summary == knowledge.summary.short


def test_shadow_service_processes_uploaded_document(
    db_session: Session,
    uploader: User,
    tmp_path: Path,
) -> None:
    sample = SAMPLE_DIR / "hr_policy.txt"
    content = sample.read_bytes()
    document_id = uuid.uuid4()
    storage = LocalStorage(base_path=tmp_path)
    storage_key = f"{document_id}.txt"
    storage.save(storage_key, content)

    db_session.add(
        Document(
            id=document_id,
            filename="hr_policy.txt",
            content_type="text/plain",
            file_size=len(content),
            checksum="shadow-checksum",
            storage_path=str(tmp_path / storage_key),
            uploaded_by=uploader.id,
            owner_id=uploader.id,
            status=DocumentStatus.SEARCHABLE.value,
            tenant_id="default",
        )
    )
    db_session.commit()

    factory = sessionmaker(
        bind=db_session.get_bind(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    service = ShadowKnowledgeService(
        storage=storage,
        session_factory=factory,
        enabled=True,
    )
    knowledge = service.process_document_id(str(document_id))
    assert knowledge is not None
    assert knowledge.document_type == DocumentType.POLICY.value

    service.on_lifecycle_event(
        DocumentUploaded(
            document_id=str(document_id),
            user_id=str(uploader.id),
            checksum="shadow-checksum",
        )
    )
    stored = KnowledgeRepository(db_session).get_by_document_id(document_id)
    assert stored is not None
    assert stored.confidence_overall > 0


def test_shadow_service_fail_open_when_disabled(db_session: Session) -> None:
    factory = sessionmaker(
        bind=db_session.get_bind(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    service = ShadowKnowledgeService(
        session_factory=factory,
        enabled=False,
    )
    assert service.process_document_id(str(uuid.uuid4())) is None
    # Must not raise even for garbage events.
    service.on_lifecycle_event(
        DocumentUploaded(document_id="not-a-uuid", user_id="x", checksum=None)
    )


def test_shadow_service_never_raises_on_missing_document(db_session: Session) -> None:
    factory = sessionmaker(
        bind=db_session.get_bind(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    service = ShadowKnowledgeService(
        session_factory=factory,
        enabled=True,
    )
    assert service.process_document_id(str(uuid.uuid4())) is None
