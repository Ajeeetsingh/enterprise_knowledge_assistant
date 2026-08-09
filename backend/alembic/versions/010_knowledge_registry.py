"""Create Knowledge Registry tables for Phase 13.2.

Revision ID: 010_knowledge_registry
Revises: 009_document_knowledge
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010_knowledge_registry"
down_revision: str | None = "009_document_knowledge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_collections",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("slug", name="uq_knowledge_collections_slug"),
    )
    op.create_index("ix_knowledge_collections_slug", "knowledge_collections", ["slug"])

    op.create_table(
        "knowledge_categories",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("collection_slug", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.Uuid(as_uuid=True), sa.ForeignKey("knowledge_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("path", name="uq_knowledge_categories_path"),
    )
    op.create_index("ix_knowledge_categories_collection_slug", "knowledge_categories", ["collection_slug"])
    op.create_index("ix_knowledge_categories_path", "knowledge_categories", ["path"])

    op.create_table(
        "knowledge_aliases",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("canonical", sa.String(length=128), nullable=False),
        sa.Column("alias", sa.String(length=128), nullable=False),
        sa.Column("normalized_alias", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("normalized_alias", name="uq_knowledge_alias_normalized"),
    )
    op.create_index("ix_knowledge_aliases_canonical", "knowledge_aliases", ["canonical"])

    op.create_table(
        "knowledge_version_groups",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_key", sa.String(length=255), nullable=False),
        sa.Column("canonical_title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("group_key", name="uq_knowledge_version_groups_key"),
    )
    op.create_index("ix_knowledge_version_groups_group_key", "knowledge_version_groups", ["group_key"])

    op.create_table(
        "knowledge_registry",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_knowledge_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("primary_collection", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("collections_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("taxonomy_path", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("categories_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("canonical_concepts_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("aliases_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("version_group_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("version_group_key", sa.String(length=255), nullable=True),
        sa.Column("version_label", sa.String(length=32), nullable=True),
        sa.Column("version_rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duplicate_of_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("duplicate_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("health_status", sa.String(length=32), nullable=False, server_default="Unknown"),
        sa.Column("needs_manual_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("registry_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("pipeline_version", sa.String(length=32), nullable=False, server_default="13.2.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_knowledge_id"], ["document_knowledge.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["version_group_id"], ["knowledge_version_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["duplicate_of_id"], ["knowledge_registry.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("document_id", name="uq_knowledge_registry_document_id"),
    )
    op.create_index("ix_knowledge_registry_document_id", "knowledge_registry", ["document_id"])
    op.create_index("ix_knowledge_registry_primary_collection", "knowledge_registry", ["primary_collection"])
    op.create_index("ix_knowledge_registry_taxonomy_path", "knowledge_registry", ["taxonomy_path"])
    op.create_index("ix_knowledge_registry_health_status", "knowledge_registry", ["health_status"])
    op.create_index("ix_knowledge_registry_version_group_key", "knowledge_registry", ["version_group_key"])


def downgrade() -> None:
    op.drop_table("knowledge_registry")
    op.drop_table("knowledge_version_groups")
    op.drop_table("knowledge_aliases")
    op.drop_table("knowledge_categories")
    op.drop_table("knowledge_collections")
