"""Message ORM model (Phase 6.1).

A Message represents one turn in a Conversation.  Every message has a role
(user / assistant / system), content text, and optional structured metadata
(citations, confidence score) persisted alongside the text.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation


class MessageRole(StrEnum):
    """Role of the message author within a conversation.

    Using a ``StrEnum`` keeps the stored values stable and avoids
    hardcoded strings scattered across the codebase.  New roles (e.g.
    ``"tool"``) can be added here without a schema migration because
    the column is a plain ``VARCHAR``.
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """One message turn within a ``Conversation``.

    Relationships:
        conversation: The parent conversation (many-to-one).
    """

    __tablename__ = "messages"

    # ------------------------------------------------------------------ #
    # Identity                                                             #
    # ------------------------------------------------------------------ #
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # ------------------------------------------------------------------ #
    # Parent reference                                                     #
    # ------------------------------------------------------------------ #
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    """FK to the parent conversation. Cascades deletion to this message."""

    # ------------------------------------------------------------------ #
    # Content                                                              #
    # ------------------------------------------------------------------ #
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    """Message role stored as the string value of ``MessageRole``."""

    content: Mapped[str] = mapped_column(Text, nullable=False)
    """Full text content of this message turn."""

    # ------------------------------------------------------------------ #
    # RAG metadata (nullable — only set on assistant messages)            #
    # ------------------------------------------------------------------ #
    _citations: Mapped[str | None] = mapped_column(
        "citations",
        Text,
        nullable=True,
    )
    """JSON-encoded list of citation objects.

    Access through the ``citations`` property which handles serialization.
    Stored as ``Text`` for portability across PostgreSQL and SQLite.
    """

    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    """RAG confidence score for the generated answer, or ``None``."""

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
    conversation: Mapped[Conversation] = relationship(
        "Conversation",
        back_populates="messages",
    )

    # ------------------------------------------------------------------ #
    # citations property                                                   #
    # ------------------------------------------------------------------ #
    @property
    def citations(self) -> list[Any]:
        """Return the deserialized list of citations, or an empty list."""
        if self._citations is None:
            return []
        try:
            result = json.loads(self._citations)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        return []

    @citations.setter
    def citations(self, value: list[Any] | None) -> None:
        """Persist *value* as a JSON string, or ``None`` to clear."""
        if value is None:
            self._citations = None
        else:
            self._citations = json.dumps(value)

    # ------------------------------------------------------------------ #
    # Convenience helper                                                   #
    # ------------------------------------------------------------------ #
    @property
    def role_enum(self) -> MessageRole | None:
        """Return the ``MessageRole`` member for the stored role string.

        Returns ``None`` when the stored value is not a recognized role
        (future-safe for roles added after this code was deployed).
        """
        try:
            return MessageRole(self.role)
        except ValueError:
            return None
