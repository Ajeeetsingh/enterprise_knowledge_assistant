"""Unit tests for Knowledge Domain repository and service (Phase 1)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import KnowledgeDomain  # noqa: F401
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository
from app.db.models.document import Document
from app.documents.status import DocumentStatus
from app.services.knowledge_domain_service import (
    DEFAULT_KNOWLEDGE_DOMAINS,
    RETIRED_DEFAULT_DOMAIN_NAMES,
    DuplicateKnowledgeDomainError,
    KnowledgeDomainService,
    KnowledgeDomainValidationError,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def service(db_session: Session) -> KnowledgeDomainService:
    return KnowledgeDomainService(KnowledgeDomainRepository(db_session))


def test_ensure_default_domains_is_idempotent(service: KnowledgeDomainService) -> None:
    first = service.ensure_default_domains()
    second = service.ensure_default_domains()
    domains = service.list_domains()

    assert first == len(DEFAULT_KNOWLEDGE_DOMAINS)
    assert second == 0
    assert len(domains) == len(DEFAULT_KNOWLEDGE_DOMAINS)
    names = [domain.name for domain in domains]
    assert names == sorted(names)
    assert names == [
        "Enterprise Governance",
        "Finance",
        "Human Resources",
    ]
    for retired in RETIRED_DEFAULT_DOMAIN_NAMES:
        assert retired not in names


def test_seeder_does_not_recreate_retired_defaults(
    service: KnowledgeDomainService,
) -> None:
    service.ensure_default_domains()
    names_before = {domain.name for domain in service.list_domains()}
    assert "IT Security" not in names_before

    # Simulate a leftover retired domain with no documents, then re-seed.
    service.create_domain(name="IT Security", description="legacy")
    assert "IT Security" in {domain.name for domain in service.list_domains()}
    removed = service.cleanup_retired_default_domains()
    assert removed == 1
    service.ensure_default_domains()
    names_after = {domain.name for domain in service.list_domains()}
    assert "IT Security" not in names_after
    assert {"Enterprise Governance", "Finance", "Human Resources"} <= names_after


def test_retired_domain_with_documents_is_kept(
    service: KnowledgeDomainService,
    db_session: Session,
) -> None:
    from uuid import uuid4

    legal = service.create_domain(name="Legal", description="legacy")
    db_session.add(
        Document(
            id=uuid4(),
            filename="contract.pdf",
            content_type="application/pdf",
            file_size=10,
            checksum="abc",
            storage_path="docs/contract.pdf",
            status=DocumentStatus.SEARCHABLE.value,
            uploaded_by=uuid4(),
            domain_id=legal.id,
        )
    )
    db_session.commit()

    removed = service.cleanup_retired_default_domains()
    assert removed == 0
    assert service._repository.find_by_name_ci("Legal") is not None


def test_admin_created_domain_survives_seeding(
    service: KnowledgeDomainService,
) -> None:
    service.ensure_default_domains()
    service.create_domain(name="Procurement", description="Vendors")
    service.ensure_default_domains()
    names = {domain.name for domain in service.list_domains()}
    assert "Procurement" in names
    assert len(names) == len(DEFAULT_KNOWLEDGE_DOMAINS) + 1


def test_create_domain_trims_and_persists(service: KnowledgeDomainService) -> None:
    domain = service.create_domain(
        name="  Procurement  ",
        description="  Vendor policies  ",
    )
    assert domain.name == "Procurement"
    assert domain.description == "Vendor policies"


def test_create_rejects_empty_name(service: KnowledgeDomainService) -> None:
    with pytest.raises(KnowledgeDomainValidationError):
        service.create_domain(name="   ")


def test_create_rejects_case_insensitive_duplicate(
    service: KnowledgeDomainService,
) -> None:
    service.create_domain(name="Legal")
    with pytest.raises(DuplicateKnowledgeDomainError):
        service.create_domain(name="legal")


def test_list_sorted_alphabetically(service: KnowledgeDomainService) -> None:
    service.create_domain(name="Zebra")
    service.create_domain(name="Alpha")
    names = [domain.name for domain in service.list_domains()]
    assert names == ["Alpha", "Zebra"]
