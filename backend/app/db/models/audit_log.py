"""AuditLog ORM model (Phase 7.1).

Persists security and operational audit events for later querying and
compliance reporting.  Integration with domain services is deferred to
later Phase 7.x tasks — this module defines the persistence foundation only.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums.audit import AuditEventCategory, AuditStatus

if TYPE_CHECKING:
    from app.db.models.user import User


class AuditLog(Base):
    """One persisted audit event.

    Relationships:
        user: Optional actor who triggered the event.  ``None`` for
            system-generated events.  Audit rows survive user deletion
            (``user_id`` is set to ``NULL`` via ``ON DELETE SET NULL``).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_event_category", "event_category"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    # ------------------------------------------------------------------ #
    # Identity                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ------------------------------------------------------------------ #
    # Event classification                                                 #
    # ------------------------------------------------------------------ #
    event_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    """Canonical event identifier (e.g. ``auth.login.success``)."""

    event_category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    """Stored string value of ``AuditEventCategory``."""

    # ------------------------------------------------------------------ #
    # Actor (optional)                                                     #
    # ------------------------------------------------------------------ #
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------ #
    # Resource context (optional)                                          #
    # ------------------------------------------------------------------ #
    resource_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Action & outcome                                                     #
    # ------------------------------------------------------------------ #
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    """Stored string value of ``AuditStatus``."""

    # ------------------------------------------------------------------ #
    # Structured context                                                   #
    # ------------------------------------------------------------------ #
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )
    """Arbitrary key/value context.  Column name ``metadata`` in the database."""

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ------------------------------------------------------------------ #
    # Timestamp                                                            #
    # ------------------------------------------------------------------ #
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    user: Mapped[User | None] = relationship(
        "User",
        back_populates="audit_logs",
    )

    # ------------------------------------------------------------------ #
    # Enum helpers                                                         #
    # ------------------------------------------------------------------ #
    @property
    def event_category_enum(self) -> AuditEventCategory | None:
        """Return the ``AuditEventCategory`` member, or ``None`` if unknown."""
        try:
            return AuditEventCategory(self.event_category)
        except ValueError:
            return None

    @property
    def status_enum(self) -> AuditStatus | None:
        """Return the ``AuditStatus`` member, or ``None`` if unknown."""
        try:
            return AuditStatus(self.status)
        except ValueError:
            return None
