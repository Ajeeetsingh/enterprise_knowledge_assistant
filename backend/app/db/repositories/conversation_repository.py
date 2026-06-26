"""Conversation repository — persistence only, no business logic."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update as sa_update
from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation


class ConversationRepository:
    """CRUD operations for ``Conversation`` records.

    This repository contains *only* persistence logic.  Authorization,
    ownership validation, and business rules belong in a future service layer.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Write operations                                                     #
    # ------------------------------------------------------------------ #

    def create(
        self,
        *,
        user_id: uuid.UUID,
        title: str | None = None,
    ) -> Conversation:
        """Persist a new conversation and return the created record.

        Args:
            user_id: UUID of the owning user.
            title: Optional human-readable title for the conversation.

        Returns:
            The newly persisted ``Conversation`` instance.
        """
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title,
        )
        self._db.add(conversation)
        self._db.commit()
        self._db.refresh(conversation)
        return conversation

    def update_title(
        self,
        conversation_id: uuid.UUID,
        title: str,
    ) -> Conversation | None:
        """Update the title and ``updated_at`` for an existing conversation.

        Args:
            conversation_id: Primary key of the conversation to update.
            title: New title (already validated by the service layer).

        Returns:
            The updated ``Conversation``, or ``None`` when no record exists.
        """
        conversation = self.get_by_id(conversation_id)
        if conversation is None:
            return None

        self._db.execute(
            sa_update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(title=title, updated_at=func.now())
        )
        self._db.commit()
        self._db.refresh(conversation)
        return conversation

    def touch(self, conversation_id: uuid.UUID) -> None:
        """Update ``updated_at`` to the current database time.

        Called after adding a message so the conversation's activity timestamp
        reflects the latest interaction.  Uses ``func.now()`` (translated by
        SQLAlchemy to the appropriate server-side expression for each dialect)
        so no Python-side timestamp is written manually.

        Args:
            conversation_id: Primary key of the conversation to touch.
        """
        self._db.execute(
            sa_update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=func.now())
        )
        self._db.commit()

    def delete(self, conversation_id: uuid.UUID) -> bool:
        """Delete a conversation and all its messages by primary key.

        Messages are removed via the ``CASCADE`` foreign key constraint and
        the ``delete-orphan`` cascade configured on the relationship.

        Args:
            conversation_id: Primary key of the conversation to remove.

        Returns:
            ``True`` when the record existed and was deleted; ``False`` when
            no matching record was found.
        """
        conversation = self.get_by_id(conversation_id)
        if conversation is None:
            return False
        self._db.delete(conversation)
        self._db.commit()
        return True

    # ------------------------------------------------------------------ #
    # Read operations                                                      #
    # ------------------------------------------------------------------ #

    def get_by_id(self, conversation_id: uuid.UUID) -> Conversation | None:
        """Return a conversation by primary key, or ``None`` if not found.

        Args:
            conversation_id: Primary key to look up.

        Returns:
            The matching ``Conversation``, or ``None``.
        """
        return self._db.get(Conversation, conversation_id)

    def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Conversation], int]:
        """Return a page of conversations owned by *user_id*.

        Conversations are ordered newest-first (``created_at DESC``).

        Args:
            user_id: Filter to conversations owned by this user.
            limit: Maximum number of records to return.
            offset: Number of records to skip (for pagination).

        Returns:
            A 2-tuple of ``(conversations, total_count)`` where
            *total_count* reflects the total number of matching records
            before pagination.
        """
        base_query = select(Conversation).where(
            Conversation.user_id == user_id
        )
        count_query = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user_id
        )

        total: int = self._db.scalar(count_query) or 0
        conversations = list(
            self._db.scalars(
                base_query
                .order_by(Conversation.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return conversations, total

    def count(self) -> int:
        """Return the total number of conversations."""
        count_query = select(func.count()).select_from(Conversation)
        return self._db.scalar(count_query) or 0
