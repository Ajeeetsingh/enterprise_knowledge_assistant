"""Create Knowledge Relationship tables for Phase 13.3.

Revision ID: 011_knowledge_relationships
Revises: 010_knowledge_registry
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011_knowledge_relationships"
down_revision: str | None = "010_knowledge_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_relationships",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source_knowledge_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("target_knowledge_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_kind", sa.String(length=32), nullable=False, server_default="heuristic_estimate"),
        sa.Column("evidence_source", sa.String(length=64), nullable=False, server_default="taxonomy"),
        sa.Column("evidence_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.String(length=64), nullable=False, server_default="relationship_engine"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("pipeline_version", sa.String(length=32), nullable=False, server_default="13.3.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["source_knowledge_id"], ["knowledge_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_knowledge_id"], ["knowledge_registry.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "source_knowledge_id",
            "target_knowledge_id",
            "relationship_type",
            name="uq_knowledge_relationship_edge",
        ),
    )
    op.create_index("ix_knowledge_relationships_source", "knowledge_relationships", ["source_knowledge_id"])
    op.create_index("ix_knowledge_relationships_target", "knowledge_relationships", ["target_knowledge_id"])
    op.create_index("ix_knowledge_relationships_type", "knowledge_relationships", ["relationship_type"])
    op.create_index("ix_knowledge_relationships_status", "knowledge_relationships", ["status"])

    op.create_table(
        "relationship_evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("relationship_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("evidence_source", sa.String(length=64), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["relationship_id"], ["knowledge_relationships.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_relationship_evidence_relationship_id", "relationship_evidence", ["relationship_id"])


def downgrade() -> None:
    op.drop_table("relationship_evidence")
    op.drop_table("knowledge_relationships")
