"""Message repository — persistence only, no business logic."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.message import Message, MessageRole


class MessageRepository:
    """CRUD operations for ``Message`` records.

    This repository contains *only* persistence logic.  Context window
    management, summarisation, and any LLM-related concerns belong in a
    future service layer.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Write operations                                                     #
    # ------------------------------------------------------------------ #

    def create(
        self,
        *,
        conversation_id: uuid.UUID,
        role: MessageRole | str,
        content: str,
        citations: list[Any] | None = None,
        confidence_score: float | None = None,
    ) -> Message:
        """Persist a new message and return the created record.

        Args:
            conversation_id: UUID of the parent conversation.
            role: The author role — a ``MessageRole`` member or its string
                value (e.g. ``"user"``, ``"assistant"``).
            content: Full text content of the message.
            citations: Optional list of citation objects (serialized as JSON).
            confidence_score: Optional RAG confidence score for assistant
                messages.

        Returns:
            The newly persisted ``Message`` instance.
        """
        role_value = role.value if isinstance(role, MessageRole) else str(role)
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role_value,
            content=content,
            confidence_score=confidence_score,
        )
        message.citations = citations
        self._db.add(message)
        self._db.commit()
        self._db.refresh(message)
        return message

    # ------------------------------------------------------------------ #
    # Read operations                                                      #
    # ------------------------------------------------------------------ #

    def list_for_conversation(
        self,
        conversation_id: uuid.UUID,
    ) -> list[Message]:
        """Return all messages in a conversation ordered by creation time.

        Messages are returned in ascending chronological order so callers
        receive them in the natural turn-by-turn sequence.

        Args:
            conversation_id: The parent conversation's primary key.

        Returns:
            List of ``Message`` instances, oldest first.
        """
        return list(
            self._db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            )
        )

    def get_recent_for_conversation(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int,
    ) -> list[Message]:
        """Return the *limit* most recent messages, ordered oldest-to-newest.

        Fetches the newest *limit* messages (``ORDER BY created_at DESC
        LIMIT limit``) then reverses the result so callers always receive
        messages in chronological order — consistent with the full history
        returned by ``list_for_conversation``.

        This is efficient for context-window construction: a single bounded
        query replaces a full-table fetch followed by a Python-side slice.

        Args:
            conversation_id: The parent conversation's primary key.
            limit: Maximum number of most-recent messages to return.
                Must be ``>= 1``; caller is responsible for validation.

        Returns:
            List of ``Message`` instances, oldest first within the window.
        """
        recent = list(
            self._db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
        )
        recent.reverse()
        return recent
