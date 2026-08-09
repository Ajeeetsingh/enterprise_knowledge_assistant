"""Create knowledge_domains table and optional documents.domain_id FK.

Revision ID: 012_knowledge_domains
Revises: 011_knowledge_relationships
Create Date: 2026-08-09

Phase 1 — Knowledge Domains foundation:

- New ``knowledge_domains`` table (id, name unique, description, timestamps)
- Nullable ``documents.domain_id`` FK → knowledge_domains.id (SET NULL)

Existing documents remain valid with ``domain_id = NULL``.
Upload and RAG behaviour are unchanged.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012_knowledge_domains"
down_revision: str | None = "011_knowledge_relationships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_domains",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_knowledge_domains_name"),
    )

    op.add_column(
        "documents",
        sa.Column("domain_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_documents_domain_id"),
        "documents",
        ["domain_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_documents_domain_id_knowledge_domains",
        "documents",
        "knowledge_domains",
        ["domain_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_documents_domain_id_knowledge_domains",
        "documents",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_documents_domain_id"), table_name="documents")
    op.drop_column("documents", "domain_id")

    op.drop_table("knowledge_domains")
