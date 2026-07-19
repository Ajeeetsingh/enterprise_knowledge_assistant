"""Add tenant-scoped active checksum uniqueness for documents.

Revision ID: 008_document_tenant_checksum_unique
Revises: 007_audit_logs
Create Date: 2026-07-19

Partial unique index on ``(tenant_id, checksum)`` for non-deleted documents
with a non-null tenant. Soft-deleted rows are excluded so content may be
re-uploaded after deletion. Different tenants may share the same checksum.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008_document_tenant_checksum_unique"
down_revision: str | None = "007_audit_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_documents_tenant_checksum_active",
        "documents",
        ["tenant_id", "checksum"],
        unique=True,
        postgresql_where=sa.text("status != 'deleted' AND tenant_id IS NOT NULL"),
        sqlite_where=sa.text("status != 'deleted' AND tenant_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_documents_tenant_checksum_active",
        table_name="documents",
    )
