"""Add document version foundation columns.

Revision ID: 004_document_version_foundation
Revises: 003_documents_table
Create Date: 2026-06-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_document_version_foundation"
down_revision: str | None = "003_documents_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "documents",
        sa.Column("parent_document_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_documents_checksum"),
        "documents",
        ["checksum"],
        unique=False,
    )
    op.create_index(
        op.f("ix_documents_parent_document_id"),
        "documents",
        ["parent_document_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_documents_parent_document_id_documents",
        "documents",
        "documents",
        ["parent_document_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_documents_parent_document_id_documents",
        "documents",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_documents_parent_document_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_checksum"), table_name="documents")
    op.drop_column("documents", "parent_document_id")
    op.drop_column("documents", "version")
