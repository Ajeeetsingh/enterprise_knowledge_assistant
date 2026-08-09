"""Business logic for Knowledge Domains (Phase 1)."""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ServiceError
from app.core.logging import get_logger, log_with_fields
from app.db.models.knowledge_domain import KnowledgeDomain
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository

logger = get_logger(__name__)

# Canonical default domains — seeded idempotently.
DEFAULT_KNOWLEDGE_DOMAINS: tuple[tuple[str, str], ...] = (
    ("Enterprise Governance", "Enterprise knowledge standards, taxonomy, and governance controls."),
    ("Human Resources", "HR policies, benefits, and workforce procedures."),
    ("Finance", "Financial policies, reporting, and controls."),
)

# Former Phase 1 defaults that must not be recreated. Deleted on seed when unused.
RETIRED_DEFAULT_DOMAIN_NAMES: tuple[str, ...] = (
    "IT Security",
    "Legal",
    "Compliance",
    "Risk",
    "Operations",
)


class KnowledgeDomainServiceError(ServiceError):
    """Base error for knowledge-domain operations."""

    public_message = "Knowledge domain operation failed."


class KnowledgeDomainValidationError(KnowledgeDomainServiceError):
    """Raised when domain input fails validation."""

    status_code = 422
    public_message = "Invalid knowledge domain."

    def __init__(self, message: str) -> None:
        self.public_message = message
        super().__init__(message)


class DuplicateKnowledgeDomainError(KnowledgeDomainServiceError):
    """Raised when a domain name already exists (case-insensitive)."""

    status_code = 409
    code = "DUPLICATE_KNOWLEDGE_DOMAIN"
    public_message = "A knowledge domain with this name already exists."

    def __init__(self, name: str) -> None:
        message = f"A knowledge domain named '{name}' already exists."
        self.public_message = message
        super().__init__(message)


class KnowledgeDomainService:
    """Application service for listing, creating, and seeding domains."""

    def __init__(self, repository: KnowledgeDomainRepository) -> None:
        self._repository = repository

    def list_domains(self) -> list[KnowledgeDomain]:
        """Return all domains sorted alphabetically by name."""
        return self._repository.list_all_ordered_by_name()

    def create_domain(
        self,
        *,
        name: str,
        description: str | None = None,
    ) -> KnowledgeDomain:
        """Create a knowledge domain after validation."""
        clean_name = self._normalize_name(name)
        clean_description = self._normalize_description(description)

        existing = self._repository.find_by_name_ci(clean_name)
        if existing is not None:
            raise DuplicateKnowledgeDomainError(existing.name)

        try:
            domain = self._repository.create(
                name=clean_name,
                description=clean_description,
            )
        except IntegrityError as exc:
            # Race: another request inserted the same name.
            raise DuplicateKnowledgeDomainError(clean_name) from exc

        log_with_fields(
            logger,
            logging.INFO,
            "Knowledge domain created",
            domain_id=str(domain.id),
            domain_name=domain.name,
        )
        return domain

    def ensure_default_domains(self) -> int:
        """Idempotently seed the canonical default domains.

        Also removes retired former defaults when they have no assigned documents.
        Admin-created domains are never removed.

        Returns:
            Number of domains newly inserted.
        """
        created = self._repository.ensure_defaults(DEFAULT_KNOWLEDGE_DOMAINS)
        if created:
            log_with_fields(
                logger,
                logging.INFO,
                "Default knowledge domains seeded",
                created_count=created,
            )
        else:
            log_with_fields(
                logger,
                logging.DEBUG,
                "Default knowledge domains already present",
                created_count=0,
            )
        removed = self.cleanup_retired_default_domains()
        if removed:
            log_with_fields(
                logger,
                logging.INFO,
                "Retired default knowledge domains removed",
                removed_count=removed,
            )
        return created

    def cleanup_retired_default_domains(self) -> int:
        """Delete retired default domains that have no assigned documents.

        Domains that still have documents are left intact and are not recreated
        later (they are absent from ``DEFAULT_KNOWLEDGE_DOMAINS``).

        Returns:
            Number of domain rows deleted.
        """
        removed = 0
        for name in RETIRED_DEFAULT_DOMAIN_NAMES:
            domain = self._repository.find_by_name_ci(name)
            if domain is None:
                continue
            document_count = self._repository.count_documents_by_domain(domain.id)
            if document_count > 0:
                log_with_fields(
                    logger,
                    logging.INFO,
                    "Skipping retired domain with assigned documents",
                    domain_id=str(domain.id),
                    domain_name=domain.name,
                    document_count=document_count,
                )
                continue
            if self._repository.delete_by_id(domain.id):
                removed += 1
        return removed

    @staticmethod
    def _normalize_name(name: str) -> str:
        if name is None:
            raise KnowledgeDomainValidationError("Domain name is required.")
        cleaned = " ".join(str(name).split())
        if not cleaned:
            raise KnowledgeDomainValidationError("Domain name must not be empty.")
        if len(cleaned) > 150:
            raise KnowledgeDomainValidationError(
                "Domain name must not exceed 150 characters."
            )
        return cleaned

    @staticmethod
    def _normalize_description(description: str | None) -> str | None:
        if description is None:
            return None
        cleaned = description.strip()
        return cleaned or None
