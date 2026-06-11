"""Initial revision — no models yet.

Revision ID: 001_initial
Revises:
Create Date: 2026-06-09

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No schema changes in Phase 1 foundation."""
    pass


def downgrade() -> None:
    """No schema changes in Phase 1 foundation."""
    pass
