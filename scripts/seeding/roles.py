"""Seed default application roles.

Usage:
    python scripts/seed_database.py --roles

Inserts Admin, Employee, HR, and Finance roles. Idempotent — skips roles
that already exist. Does not create users.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.db.models import Role
from app.db.session import SessionLocal

DEFAULT_ROLES: tuple[tuple[str, str], ...] = (
    ("Admin", "Platform administrator with full access"),
    ("Employee", "Standard employee access"),
    ("HR", "Human resources team member"),
    ("Finance", "Finance team member"),
)


def seed_roles() -> int:
    """Insert default roles if they do not already exist."""
    created = 0
    with SessionLocal() as session:
        for name, description in DEFAULT_ROLES:
            existing = session.scalar(select(Role).where(Role.name == name))
            if existing is not None:
                print(f"  skip  {name} (already exists)")
                continue
            session.add(Role(name=name, description=description))
            created += 1
            print(f"  added {name}")
        session.commit()
    print(f"Done. {created} role(s) created.")
    return 0


def main() -> int:
    print("Seeding default roles...")
    return seed_roles()


if __name__ == "__main__":
    sys.exit(main())
