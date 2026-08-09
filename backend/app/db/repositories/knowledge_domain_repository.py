"""Persistence helpers for Knowledge Domains."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.knowledge_domain import KnowledgeDomain


class KnowledgeDomainRepository:
    """CRUD and query operations for ``KnowledgeDomain`` rows."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all_ordered_by_name(self) -> list[KnowledgeDomain]:
        """Return all domains sorted alphabetically by name."""
        stmt = select(KnowledgeDomain).order_by(KnowledgeDomain.name.asc())
        return list(self._db.scalars(stmt))

    def get_by_id(self, domain_id: uuid.UUID) -> KnowledgeDomain | None:
        return self._db.get(KnowledgeDomain, domain_id)

    def find_by_name_ci(self, name: str) -> KnowledgeDomain | None:
        """Case-insensitive name lookup."""
        normalized = name.strip()
        if not normalized:
            return None
        stmt = select(KnowledgeDomain).where(
            func.lower(KnowledgeDomain.name) == normalized.lower()
        )
        return self._db.scalar(stmt)

    def create(
        self,
        *,
        name: str,
        description: str | None,
    ) -> KnowledgeDomain:
        domain = KnowledgeDomain(
            id=uuid.uuid4(),
            name=name,
            description=description,
        )
        self._db.add(domain)
        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        self._db.refresh(domain)
        return domain

    def ensure_defaults(
        self,
        defaults: tuple[tuple[str, str | None], ...],
    ) -> int:
        """Insert missing default domains. Returns number of rows created."""
        created = 0
        for name, description in defaults:
            if self.find_by_name_ci(name) is not None:
                continue
            self._db.add(
                KnowledgeDomain(
                    id=uuid.uuid4(),
                    name=name,
                    description=description,
                )
            )
            created += 1
        if created:
            self._db.commit()
        return created

    def count_documents_by_domain(self, domain_id: uuid.UUID) -> int:
        """Return how many documents currently reference *domain_id*."""
        stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.domain_id == domain_id)
        )
        return int(self._db.scalar(stmt) or 0)

    def delete_by_id(self, domain_id: uuid.UUID) -> bool:
        """Delete a domain row by ID. Returns True when a row was deleted."""
        domain = self.get_by_id(domain_id)
        if domain is None:
            return False
        self._db.delete(domain)
        try:
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return True
