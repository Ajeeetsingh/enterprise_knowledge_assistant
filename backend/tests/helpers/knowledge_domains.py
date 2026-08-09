"""Test helpers for Knowledge Domain fixtures used by upload tests."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.db.models.knowledge_domain import KnowledgeDomain
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository


def make_knowledge_domain(
    session: Session,
    *,
    name: str | None = None,
) -> KnowledgeDomain:
    """Insert and return a knowledge domain for tests."""
    domain = KnowledgeDomain(
        id=uuid.uuid4(),
        name=name or f"Test Domain {uuid.uuid4().hex[:8]}",
        description="Test knowledge domain",
    )
    session.add(domain)
    session.commit()
    session.refresh(domain)
    return domain


def domain_upload_kwargs(
    session: Session,
    domain: KnowledgeDomain | None = None,
) -> dict:
    """Keyword args required by ``DocumentService.upload_document``."""
    resolved = domain or make_knowledge_domain(session)
    return {
        "domain_id": resolved.id,
        "domain_repository": KnowledgeDomainRepository(session),
    }
