"""Conversation business logic (Phase 6.2 / Phase 6.3 / Phase 6.4).

Orchestrates ``ConversationRepository`` and ``MessageRepository`` to implement
ownership-enforced conversation management, message persistence, and
context assembly for context-aware RAG queries.

Design constraints:
- No FastAPI imports — this module is framework-agnostic.
- No SQLAlchemy queries — all persistence goes through the repository layer.
- No RAG, LLM, or retrieval logic.
- Message schema / request-response types are out of scope (Phase 6.5+).
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConversationAccessDeniedError,
    ConversationNotFoundError,
    ConversationValidationError,
    InvalidConfidenceScoreError,
    MessageValidationError,
)
from app.core.logging import get_logger
from app.db.models.conversation import Conversation
from app.db.models.message import Message, MessageRole
from app.db.models.user import User
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.services.context_builder import (
    DEFAULT_CONTEXT_WINDOW,
    MAX_CONTEXT_CHARACTERS,
    MAX_CONTEXT_WINDOW,
    ContextBuilder,
    ConversationContext,
)

logger = get_logger(__name__)

# Pagination defaults — consistent with DocumentService.
DEFAULT_LIST_LIMIT: int = 20
MAX_LIST_LIMIT: int = 100

# Title constraints — consistent with the ``String(500)`` column definition.
MAX_TITLE_LENGTH: int = 500

# Recent-message window constraints.
MAX_RECENT_MESSAGES: int = 200


class ConversationService:
    """Business logic for conversation and message management.

    Every method enforces strict ownership isolation: a user may only operate
    on conversations they own.  No administrator bypass is provided at this
    layer.

    Phase 6.2 responsibilities: create, get, list, delete conversations.
    Phase 6.7 responsibilities: rename conversations.
    Phase 6.3 responsibilities: add messages, retrieve history, retrieve
    recent messages.
    Phase 6.4 responsibilities: build context-aware queries via ContextBuilder.

    Dependencies:
        conversation_repo: Persistence layer for ``Conversation`` records.
        message_repo: Persistence layer for ``Message`` records.
    """

    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def create_conversation(
        self,
        user: User,
        title: str | None = None,
    ) -> Conversation:
        """Create a new conversation owned by *user*.

        Title handling:
        - Leading/trailing whitespace is stripped.
        - A blank string after stripping is treated as ``None``.
        - Titles exceeding ``MAX_TITLE_LENGTH`` raise
          ``ConversationValidationError``.

        Args:
            user: The authenticated owner of the new conversation.
            title: Optional human-readable title.

        Returns:
            The newly persisted ``Conversation``.

        Raises:
            ConversationValidationError: When the title exceeds the maximum
                allowed length.
        """
        clean_title = self._normalize_title(title)

        conversation = self._conversation_repo.create(
            user_id=user.id,
            title=clean_title,
        )
        logger.debug(
            "conversation.created",
            extra={"conversation_id": str(conversation.id), "user_id": str(user.id)},
        )
        return conversation

    def get_conversation(
        self,
        user: User,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        """Return the conversation identified by *conversation_id*.

        Args:
            user: The authenticated user making the request.
            conversation_id: Primary key of the target conversation.

        Returns:
            The ``Conversation`` when it exists and is owned by *user*.

        Raises:
            ConversationNotFoundError: When no conversation with the given ID
                exists in the database.
            ConversationAccessDeniedError: When the conversation exists but
                belongs to a different user.
        """
        return self._get_owned_conversation(user, conversation_id)

    def list_conversations(
        self,
        user: User,
        *,
        limit: int = DEFAULT_LIST_LIMIT,
        offset: int = 0,
    ) -> tuple[list[Conversation], int]:
        """Return a page of conversations owned by *user*, newest first.

        Only conversations belonging to *user* are returned regardless of
        what other conversations exist in the database.

        Args:
            user: The authenticated user whose conversations to list.
            limit: Maximum number of records to return.  Clamped to
                ``[1, MAX_LIST_LIMIT]``.
            offset: Number of records to skip for pagination.  Clamped to
                ``>= 0``.

        Returns:
            A 2-tuple ``(conversations, total_count)`` where *total_count*
            is the total number of the user's conversations before pagination.
        """
        safe_limit = max(1, min(limit, MAX_LIST_LIMIT))
        safe_offset = max(0, offset)

        return self._conversation_repo.list_by_user(
            user.id,
            limit=safe_limit,
            offset=safe_offset,
        )

    def delete_conversation(
        self,
        user: User,
        conversation_id: uuid.UUID,
    ) -> bool:
        """Delete a conversation and all its messages.

        Cascading deletion of messages is handled at the database layer via
        the ``ON DELETE CASCADE`` foreign key constraint.

        Args:
            user: The authenticated user requesting the deletion.
            conversation_id: Primary key of the conversation to delete.

        Returns:
            ``True`` when the conversation was found and deleted.

        Raises:
            ConversationNotFoundError: When no conversation with the given ID
                exists.
            ConversationAccessDeniedError: When the conversation exists but
                belongs to a different user.
        """
        conversation = self._get_owned_conversation(user, conversation_id)
        deleted = self._conversation_repo.delete(conversation.id)
        if deleted:
            logger.debug(
                "conversation.deleted",
                extra={
                    "conversation_id": str(conversation_id),
                    "user_id": str(user.id),
                },
            )
        return deleted

    def rename_conversation(
        self,
        user: User,
        conversation_id: uuid.UUID,
        title: str,
    ) -> Conversation:
        """Rename an owned conversation.

        Args:
            user: The authenticated user requesting the rename.
            conversation_id: Primary key of the conversation to rename.
            title: New title. Leading/trailing whitespace is stripped.

        Returns:
            The updated ``Conversation``.

        Raises:
            ConversationNotFoundError: When no conversation with the given ID
                exists.
            ConversationAccessDeniedError: When the conversation exists but
                belongs to a different user.
            ConversationValidationError: When *title* is blank or exceeds
                ``MAX_TITLE_LENGTH``.
        """
        conversation = self._get_owned_conversation(user, conversation_id)
        clean_title = self._validate_rename_title(title)

        updated = self._conversation_repo.update_title(conversation.id, clean_title)
        if updated is None:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found."
            )

        logger.debug(
            "conversation.renamed",
            extra={
                "conversation_id": str(conversation_id),
                "user_id": str(user.id),
            },
        )
        return updated

    def set_auto_generated_title(
        self,
        user: User,
        conversation_id: uuid.UUID,
        title: str,
    ) -> Conversation | None:
        """Set an auto-generated title, but only when the conversation has none yet.

        Safe to call unconditionally after every user message: once a title
        exists — whether set by the user via ``rename_conversation`` or by a
        prior successful auto-generation — this is a no-op. That single
        guarantee is what makes a conversation's title get generated
        exactly once, without any separate "already generated" flag or
        bookkeeping.

        Args:
            user: The authenticated user who owns the conversation.
            conversation_id: Primary key of the target conversation.
            title: Generated title text. Whitespace is stripped and the
                result is truncated to ``MAX_TITLE_LENGTH`` defensively —
                generated titles are always short in practice, so this
                should never actually trigger.

        Returns:
            The updated ``Conversation`` when the title was set, or
            ``None`` when the conversation already had a title (no-op) or
            *title* was blank after stripping.

        Raises:
            ConversationNotFoundError: When the conversation does not exist.
            ConversationAccessDeniedError: When the conversation belongs to
                a different user.
        """
        conversation = self._get_owned_conversation(user, conversation_id)
        if conversation.title is not None:
            return None

        clean_title = title.strip()[:MAX_TITLE_LENGTH]
        if not clean_title:
            return None

        updated = self._conversation_repo.set_title_if_unset(conversation.id, clean_title)
        if updated is not None:
            logger.debug(
                "conversation.auto_titled",
                extra={"conversation_id": str(conversation_id), "user_id": str(user.id)},
            )
        return updated

    # ------------------------------------------------------------------ #
    # Message management (Phase 6.3)                                      #
    # ------------------------------------------------------------------ #

    def add_user_message(
        self,
        user: User,
        conversation_id: uuid.UUID,
        content: str,
    ) -> Message:
        """Append a ``USER`` message to an owned conversation.

        Args:
            user: The authenticated user sending the message.
            conversation_id: Primary key of the target conversation.
            content: Raw message text. Leading/trailing whitespace is trimmed.

        Returns:
            The newly persisted ``Message``.

        Raises:
            ConversationNotFoundError: When the conversation does not exist.
            ConversationAccessDeniedError: When the conversation belongs to a
                different user.
            MessageValidationError: When *content* is empty or blank.
        """
        conversation = self._get_owned_conversation(user, conversation_id)
        clean_content = self._validate_content(content)

        message = self._message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=clean_content,
        )
        self._conversation_repo.touch(conversation.id)
        return message

    def add_assistant_message(
        self,
        user: User,
        conversation_id: uuid.UUID,
        content: str,
        citations: list | None = None,
        confidence_score: float | None = None,
    ) -> Message:
        """Append an ``ASSISTANT`` message to an owned conversation.

        Args:
            user: The authenticated user who owns the conversation.
            conversation_id: Primary key of the target conversation.
            content: Answer text from the assistant. Trimmed of whitespace.
            citations: Optional list of citation objects from the RAG engine.
            confidence_score: Optional answer confidence in the range
                ``[0.0, 1.0]``.

        Returns:
            The newly persisted ``Message``.

        Raises:
            ConversationNotFoundError: When the conversation does not exist.
            ConversationAccessDeniedError: When the conversation belongs to a
                different user.
            MessageValidationError: When *content* is empty or blank.
            InvalidConfidenceScoreError: When *confidence_score* is outside
                the range ``[0.0, 1.0]``.
        """
        conversation = self._get_owned_conversation(user, conversation_id)
        clean_content = self._validate_content(content)
        self._validate_confidence_score(confidence_score)

        message = self._message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=clean_content,
            citations=citations,
            confidence_score=confidence_score,
        )
        self._conversation_repo.touch(conversation.id)
        return message

    def get_conversation_history(
        self,
        user: User,
        conversation_id: uuid.UUID,
    ) -> list[Message]:
        """Return all messages for an owned conversation, oldest first.

        The ordering is deterministic: messages are sorted by ``created_at``
        ascending so the returned list reproduces the natural turn-by-turn
        sequence of the conversation.

        Args:
            user: The authenticated user requesting history.
            conversation_id: Primary key of the target conversation.

        Returns:
            List of ``Message`` instances ordered oldest-to-newest.

        Raises:
            ConversationNotFoundError: When the conversation does not exist.
            ConversationAccessDeniedError: When the conversation belongs to a
                different user.
        """
        self._get_owned_conversation(user, conversation_id)
        return self._message_repo.list_for_conversation(conversation_id)

    def get_recent_messages(
        self,
        user: User,
        conversation_id: uuid.UUID,
        limit: int,
    ) -> list[Message]:
        """Return the *limit* most recent messages, ordered oldest-to-newest.

        Designed as a foundation for future context-window construction.
        Given a conversation with 50 messages and ``limit=10``, the last 10
        messages are returned in chronological order (message 41 → 50).

        Args:
            user: The authenticated user requesting recent messages.
            conversation_id: Primary key of the target conversation.
            limit: Maximum number of recent messages to return. Clamped to
                ``[1, MAX_RECENT_MESSAGES]``.

        Returns:
            List of ``Message`` instances ordered oldest-to-newest within the
            window.

        Raises:
            ConversationNotFoundError: When the conversation does not exist.
            ConversationAccessDeniedError: When the conversation belongs to a
                different user.
        """
        self._get_owned_conversation(user, conversation_id)
        safe_limit = max(1, min(limit, MAX_RECENT_MESSAGES))
        return self._message_repo.get_recent_for_conversation(
            conversation_id,
            limit=safe_limit,
        )

    # ------------------------------------------------------------------ #
    # Context management (Phase 6.4)                                      #
    # ------------------------------------------------------------------ #

    def build_conversation_context(
        self,
        user: User,
        conversation_id: uuid.UUID,
        current_question: str,
        *,
        window_size: int = DEFAULT_CONTEXT_WINDOW,
        max_chars: int = MAX_CONTEXT_CHARACTERS,
    ) -> ConversationContext:
        """Build a context-aware query by combining recent history with *current_question*.

        Steps:
        1. Validate *current_question* (non-empty after stripping).
        2. Verify ownership of *conversation_id*.
        3. Retrieve the *window_size* most recent messages.
        4. Delegate to ``ContextBuilder.build`` to assemble the context.

        The returned ``ConversationContext.context_query`` is ready to be
        forwarded to the RAG service as the enriched query in a future phase.
        No RAG calls are made here.

        Args:
            user: The authenticated user making the request.
            conversation_id: Primary key of the target conversation.
            current_question: The question being asked now. Leading/trailing
                whitespace is stripped before use.
            window_size: How many recent messages to include.  Clamped to
                ``[1, MAX_CONTEXT_WINDOW]``.
            max_chars: Maximum length of the assembled ``context_query``.
                Defaults to ``MAX_CONTEXT_CHARACTERS``.

        Returns:
            A ``ConversationContext`` containing the assembled query, the
            included history messages, and metadata about truncation.

        Raises:
            MessageValidationError: When *current_question* is empty or blank.
            ConversationNotFoundError: When the conversation does not exist.
            ConversationAccessDeniedError: When the conversation belongs to a
                different user.
        """
        clean_question = self._validate_content(current_question)

        self._get_owned_conversation(user, conversation_id)

        safe_window = max(1, min(window_size, MAX_CONTEXT_WINDOW))
        recent = self._message_repo.get_recent_for_conversation(
            conversation_id,
            limit=safe_window,
        )

        return ContextBuilder.build(
            clean_question,
            recent,
            max_chars=max_chars,
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _get_owned_conversation(
        self,
        user: User,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        """Fetch and ownership-check a conversation in one call.

        Combines the ``get_by_id`` lookup with ``_assert_ownership`` so that
        all methods that need a verified conversation can share a single path.

        Args:
            user: The requesting user.
            conversation_id: Primary key to look up.

        Returns:
            The verified ``Conversation``.

        Raises:
            ConversationNotFoundError: When the conversation does not exist.
            ConversationAccessDeniedError: When the conversation belongs to
                a different user.
        """
        conversation = self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found."
            )
        self._assert_ownership(user, conversation)
        return conversation

    def _assert_ownership(self, user: User, conversation: Conversation) -> None:
        """Raise ``ConversationAccessDeniedError`` when *user* does not own
        *conversation*.

        Args:
            user: The requesting user.
            conversation: The conversation whose ownership to verify.

        Raises:
            ConversationAccessDeniedError: When ``conversation.user_id`` does
                not match ``user.id``.
        """
        if conversation.user_id != user.id:
            logger.warning(
                "conversation.access_denied",
                extra={
                    "conversation_id": str(conversation.id),
                    "owner_id": str(conversation.user_id),
                    "requester_id": str(user.id),
                },
            )
            raise ConversationAccessDeniedError(
                f"User {user.id} does not own conversation {conversation.id}."
            )

    @staticmethod
    def _validate_content(content: str) -> str:
        """Strip whitespace and reject blank message content.

        Args:
            content: Raw message text from the caller.

        Returns:
            Content stripped of leading/trailing whitespace.

        Raises:
            MessageValidationError: When *content* is ``None``, empty, or
                contains only whitespace after stripping.
        """
        if not content or not content.strip():
            raise MessageValidationError(
                "Message content must not be empty or blank."
            )
        return content.strip()

    @staticmethod
    def _validate_confidence_score(score: float | None) -> None:
        """Raise when *score* is outside the valid range [0.0, 1.0].

        ``None`` is explicitly allowed (no score provided).

        Args:
            score: Confidence score to validate, or ``None``.

        Raises:
            InvalidConfidenceScoreError: When *score* is not in [0.0, 1.0].
        """
        if score is None:
            return
        if not (0.0 <= score <= 1.0):
            raise InvalidConfidenceScoreError(
                f"Confidence score must be in [0.0, 1.0], got {score}."
            )

    @staticmethod
    def _normalize_title(title: str | None) -> str | None:
        """Strip whitespace and enforce ``MAX_TITLE_LENGTH``.

        Args:
            title: Raw title string from the caller, or ``None``.

        Returns:
            Cleaned title string, or ``None`` when the input was absent or
            blank after stripping.

        Raises:
            ConversationValidationError: When the stripped title exceeds
                ``MAX_TITLE_LENGTH`` characters.
        """
        if title is None:
            return None
        stripped = title.strip()
        if not stripped:
            return None
        if len(stripped) > MAX_TITLE_LENGTH:
            raise ConversationValidationError(
                f"Conversation title must not exceed {MAX_TITLE_LENGTH} characters "
                f"(got {len(stripped)})."
            )
        return stripped

    @staticmethod
    def _validate_rename_title(title: str) -> str:
        """Strip whitespace and enforce required title constraints for rename.

        Unlike ``_normalize_title``, blank input is rejected because rename
        requires an explicit non-empty title.

        Args:
            title: Raw title string from the caller.

        Returns:
            Cleaned title string.

        Raises:
            ConversationValidationError: When *title* is blank or exceeds
                ``MAX_TITLE_LENGTH``.
        """
        stripped = title.strip()
        if not stripped:
            raise ConversationValidationError(
                "Conversation title must not be empty or blank."
            )
        if len(stripped) > MAX_TITLE_LENGTH:
            raise ConversationValidationError(
                f"Conversation title must not exceed {MAX_TITLE_LENGTH} characters "
                f"(got {len(stripped)})."
            )
        return stripped


def build_conversation_service(db: Session) -> ConversationService:
    """Construct a ``ConversationService`` bound to *db*.

    Used by FastAPI dependency injection to wire repositories per request.

    Args:
        db: Active SQLAlchemy session for the current request.

    Returns:
        A fully wired ``ConversationService`` instance.
    """
    return ConversationService(
        conversation_repo=ConversationRepository(db),
        message_repo=MessageRepository(db),
    )
