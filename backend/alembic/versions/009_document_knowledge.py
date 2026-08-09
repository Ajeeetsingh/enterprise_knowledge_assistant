"""Create document_knowledge table for Phase 13.1 Knowledge Engine.

Revision ID: 009_document_knowledge
Revises: 008_document_tenant_checksum_unique
Create Date: 2026-07-26

Stores shadow-mode Knowledge Objects independently of the documents table
and the legacy ingestion/retrieval path.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009_document_knowledge"
down_revision: str | None = "008_document_tenant_checksum_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_knowledge",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("knowledge_json", sa.Text(), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=False, server_default="Unknown"),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("short_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("departments_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("topics_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("keywords_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("confidence_overall", sa.Float(), nullable=False, server_default="0"),
        sa.Column("pipeline_version", sa.String(length=32), nullable=False, server_default="13.1.0"),
        sa.Column("model_used", sa.String(length=64), nullable=False, server_default="heuristic-v1"),
        sa.Column("processing_time_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="success"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", name="uq_document_knowledge_document_id"),
    )
    op.create_index("ix_document_knowledge_document_id", "document_knowledge", ["document_id"])
    op.create_index("ix_document_knowledge_document_type", "document_knowledge", ["document_type"])
    op.create_index("ix_document_knowledge_status", "document_knowledge", ["status"])


def downgrade() -> None:
    op.drop_index("ix_document_knowledge_status", table_name="document_knowledge")
    op.drop_index("ix_document_knowledge_document_type", table_name="document_knowledge")
    op.drop_index("ix_document_knowledge_document_id", table_name="document_knowledge")
    op.drop_table("document_knowledge")
