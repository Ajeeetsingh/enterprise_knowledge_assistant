"""Seed demo users for manual RBAC and analytics testing.

Usage:
    python scripts/seed_database.py --demo

Requires roles (``seed_database.py --roles``) and optionally the admin user
(``seed_database.py --admin``). Idempotent — skips users that already exist.

All demo accounts use password: DemoPass1!
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import hash_password
from app.db.models import Role, User
from app.db.session import SessionLocal

DEMO_PASSWORD = "DemoPass1!"


@dataclass(frozen=True)
class DemoUserSpec:
    email: str
    username: str
    full_name: str
    role_name: str


DEMO_USERS: tuple[DemoUserSpec, ...] = (
    DemoUserSpec(
        email="hr@example.com",
        username="hr",
        full_name="HR User",
        role_name="HR",
    ),
    DemoUserSpec(
        email="finance@example.com",
        username="finance",
        full_name="Finance User",
        role_name="Finance",
    ),
    DemoUserSpec(
        email="employee@example.com",
        username="employee",
        full_name="Employee User",
        role_name="Employee",
    ),
    DemoUserSpec(
        email="quiet@example.com",
        username="quiet",
        full_name="Quiet Employee",
        role_name="Employee",
    ),
)


def seed_demo_users() -> int:
    """Create demo users for manual testing if they do not already exist."""
    created = 0
    with SessionLocal() as session:
        roles = {
            role.name: role
            for role in session.scalars(select(Role)).all()
        }

        for spec in DEMO_USERS:
            role = roles.get(spec.role_name)
            if role is None:
                print(
                    f"Error: Role '{spec.role_name}' not found. "
                    "Run `python scripts/seed_database.py --roles` first."
                )
                return 1

            existing = session.scalar(
                select(User)
                .where(User.email == spec.email)
                .options(selectinload(User.roles))
            )
            if existing is not None:
                print(f"  skip  {spec.email} (already exists)")
                continue

            user = User(
                email=spec.email,
                username=spec.username,
                full_name=spec.full_name,
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
                is_superuser=False,
            )
            user.roles.append(role)
            session.add(user)
            created += 1
            print(f"  added {spec.email} ({spec.role_name})")

        session.commit()

    print(f"Done. {created} demo user(s) created.")
    print(f"Demo password for all accounts: {DEMO_PASSWORD}")
    return 0


def main() -> int:
    print("Seeding demo users...")
    return seed_demo_users()


if __name__ == "__main__":
    sys.exit(main())
