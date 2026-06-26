"""Add audit_logs table (Phase 7.1).

Revision ID: 007_audit_logs
Revises: 006_conversation_tables
Create Date: 2026-06-23

Creates the ``audit_logs`` table for persisted audit event history.

Enum columns (``event_category``, ``status``) are stored as ``VARCHAR``
values — consistent with other StrEnum-backed columns in this project
(``MessageRole``, ``DocumentVisibility``).  No native PostgreSQL enum
types are created, keeping SQLite test compatibility and simplifying
future enum extensions.

Indexes created:
    - ``ix_audit_logs_event_type``
    - ``ix_audit_logs_event_category``
    - ``ix_audit_logs_user_id``
    - ``ix_audit_logs_created_at``

Foreign keys:
    - ``user_id`` → ``users.id`` with ``ON DELETE SET NULL`` so audit
      history survives user account deletion.

No existing tables are modified.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_audit_logs"
down_revision: str | None = "006_conversation_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("event_category", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("resource_type", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_event_type"),
        "audit_logs",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_event_category"),
        "audit_logs",
        ["event_category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_user_id"),
        "audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_created_at"),
        "audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_event_category"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_event_type"), table_name="audit_logs")
    op.drop_table("audit_logs")
