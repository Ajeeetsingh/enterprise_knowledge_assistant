"""Seed the default admin user for local development and manual testing.

Usage:
    python scripts/seed_admin_user.py

Creates admin@example.com with the Admin role. Idempotent — skips if the
user already exists. Requires roles to be seeded first via seed_roles.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.auth import hash_password
from app.db.models import Role, User
from app.db.session import SessionLocal

ADMIN_EMAIL = "admin@example.com"
ADMIN_USERNAME = "admin"
ADMIN_FULL_NAME = "Admin User"
ADMIN_PASSWORD = "AdminPass1!"
ADMIN_ROLE_NAME = "Admin"


def seed_admin_user() -> int:
    """Create the default admin user if it does not already exist."""
    with SessionLocal() as session:
        admin_role = session.scalar(
            select(Role).where(Role.name == ADMIN_ROLE_NAME)
        )
        if admin_role is None:
            print(
                "Error: Admin role not found. "
                "Run `python scripts/seed_roles.py` first."
            )
            return 1

        existing = session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if existing is not None:
            print("Admin user already exists.")
            return 0

        user = User(
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            full_name=ADMIN_FULL_NAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            is_active=True,
            is_superuser=True,
        )
        user.roles.append(admin_role)
        session.add(user)
        session.commit()

    print("Admin user created successfully.")
    return 0


def main() -> int:
    print("Seeding admin user...")
    return seed_admin_user()


if __name__ == "__main__":
    sys.exit(main())
