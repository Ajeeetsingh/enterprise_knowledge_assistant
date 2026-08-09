"""Request-scoped signal inputs for DOCUMENT vs GENERAL classification."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.query_router.document_catalog import DocumentRouteCatalog


@dataclass(frozen=True)
class RouteSignalContext:
    """Tenant-agnostic inputs that enrich routing without hardcoding org names."""

    has_accessible_documents: bool = False
    org_aliases: tuple[str, ...] = ()
    catalog: DocumentRouteCatalog = field(default_factory=DocumentRouteCatalog)
    # When False, skip embedding-based enterprise intent (tests / fail-open).
    enable_semantic_enterprise_intent: bool = True
