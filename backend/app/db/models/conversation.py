"""Conversation ORM model (Phase 6.1).

A Conversation represents one chat session owned by a single user.
Messages are cascade-deleted when their parent conversation is deleted.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.user import User


class Conversation(Base):
    """A chat session belonging to exactly one authenticated user.

    Relationships:
        user:     The owner of this conversation (many-to-one).
        messages: All messages within this conversation (one-to-many,
                  cascade delete-orphan).
    """

    __tablename__ = "conversations"

    # ------------------------------------------------------------------ #
    # Identity                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ------------------------------------------------------------------ #
    # Ownership                                                            #
    # ------------------------------------------------------------------ #
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    """FK to the owning user. Cascades deletion to this conversation."""

    # ------------------------------------------------------------------ #
    # Metadata                                                             #
    # ------------------------------------------------------------------ #
    title: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    """Optional human-readable title. May be set by the client or
    auto-generated in a future phase."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    user: Mapped[User] = relationship(
        "User",
        back_populates="conversations",
    )

    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
