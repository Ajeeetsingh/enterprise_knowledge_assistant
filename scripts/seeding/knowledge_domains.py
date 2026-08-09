"""Seed default Knowledge Domains.

Usage:
    python scripts/seed_database.py --domains

Inserts the canonical Phase 1 domains when missing. Idempotent — never
creates duplicates (case-insensitive name match).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository
from app.db.session import SessionLocal
from app.services.knowledge_domain_service import (
    DEFAULT_KNOWLEDGE_DOMAINS,
    RETIRED_DEFAULT_DOMAIN_NAMES,
    KnowledgeDomainService,
)


def seed_knowledge_domains() -> int:
    """Insert default knowledge domains if they do not already exist."""
    with SessionLocal() as session:
        repository = KnowledgeDomainRepository(session)
        service = KnowledgeDomainService(repository)
        existing_names = {
            domain.name.casefold() for domain in service.list_domains()
        }
        for name, _description in DEFAULT_KNOWLEDGE_DOMAINS:
            if name.casefold() in existing_names:
                print(f"  skip  {name} (already exists)")
            else:
                print(f"  add   {name}")
        for name in RETIRED_DEFAULT_DOMAIN_NAMES:
            if name.casefold() in existing_names:
                print(f"  retire {name} (removed when unused)")
        created = service.ensure_default_domains()
        remaining = {domain.name for domain in service.list_domains()}
    print(f"Done. {created} knowledge domain(s) created.")
    print(f"Current domains: {', '.join(sorted(remaining))}")
    return 0


def main() -> int:
    print("Seeding default knowledge domains...")
    return seed_knowledge_domains()


if __name__ == "__main__":
    sys.exit(main())
