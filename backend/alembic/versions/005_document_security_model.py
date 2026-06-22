"""Add document security model columns (Phase 5.2).

Revision ID: 005_document_security_model
Revises: 004_document_version_foundation
Create Date: 2026-06-22

Adds four security metadata columns to the ``documents`` table:

- ``department``    — nullable VARCHAR(100), indexed
- ``owner_id``      — nullable UUID FK → users.id (SET NULL on delete)
- ``visibility``    — VARCHAR(20) NOT NULL, default 'restricted', indexed
- ``allowed_roles`` — nullable TEXT (JSON-encoded role list)

All existing rows receive safe defaults:
- ``department``    → NULL
- ``owner_id``      → NULL (no owner reassignment; uploader remains)
- ``visibility``    → 'restricted'
- ``allowed_roles`` → NULL  (treated as empty list by the ORM property)

The migration is fully reversible.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_document_security_model"
down_revision: str | None = "004_document_version_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # department — optional owning department
    op.add_column(
        "documents",
        sa.Column("department", sa.String(length=100), nullable=True),
    )
    op.create_index(
        op.f("ix_documents_department"),
        "documents",
        ["department"],
        unique=False,
    )

    # owner_id — FK to users; SET NULL preserves document if owner is removed
    op.add_column(
        "documents",
        sa.Column("owner_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_documents_owner_id"),
        "documents",
        ["owner_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_documents_owner_id_users",
        "documents",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # visibility — stored as plain string for portability; default 'restricted'
    op.add_column(
        "documents",
        sa.Column(
            "visibility",
            sa.String(length=20),
            nullable=False,
            server_default="restricted",
        ),
    )
    op.create_index(
        op.f("ix_documents_visibility"),
        "documents",
        ["visibility"],
        unique=False,
    )

    # allowed_roles — JSON-encoded list of role name strings
    op.add_column(
        "documents",
        sa.Column("allowed_roles", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "allowed_roles")
    op.drop_index(op.f("ix_documents_visibility"), table_name="documents")
    op.drop_column("documents", "visibility")
    op.drop_constraint(
        "fk_documents_owner_id_users",
        "documents",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_documents_owner_id"), table_name="documents")
    op.drop_column("documents", "owner_id")
    op.drop_index(op.f("ix_documents_department"), table_name="documents")
    op.drop_column("documents", "department")
