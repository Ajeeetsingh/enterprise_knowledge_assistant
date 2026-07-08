"""Conversation context builder (Phase 6.4).

Assembles a context-aware query from recent conversation messages and the
current user question so that the RAG service can provide relevant,
coherent follow-up answers.

Design invariants:
- No LLM calls, no network I/O, no database access.
- Fully deterministic: same inputs always produce the same output.
- Stateless: all logic is in static methods; the class holds no instance state.
- Independent of FastAPI, SQLAlchemy sessions, and the RAG engine.
- Unit-testable without any application infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.db.models.message import Message, MessageRole

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

#: Default number of recent messages included in the context window.
#: Callers can override per-request; this is the built-in safe default.
DEFAULT_CONTEXT_WINDOW: int = 10

#: Hard ceiling on how many messages a caller may request in the window.
#: Prevents accidental full-history dumps into the context.
MAX_CONTEXT_WINDOW: int = 50

#: Maximum total characters of the assembled ``context_query`` string,
#: including role labels, section headers, line breaks, the current-question
#: prefix, and question text.  When exceeded the oldest messages are dropped
#: first; the question text is truncated only if the limit is still exceeded
#: with no history.
MAX_CONTEXT_CHARACTERS: int = 8_000

# ---------------------------------------------------------------------------
# Role labels used in the formatted context string
# ---------------------------------------------------------------------------

_ROLE_LABELS: dict[str, str] = {
    MessageRole.USER: "User",
    MessageRole.ASSISTANT: "Assistant",
    MessageRole.SYSTEM: "System",
}

_UNKNOWN_ROLE_LABEL: str = "Unknown"

_CONTEXT_HEADER: str = "Conversation context:"
_CURRENT_QUESTION_PREFIX: str = "Current question:"


# ---------------------------------------------------------------------------
# ConversationContext result type
# ---------------------------------------------------------------------------


@dataclass
class ConversationContext:
    """The assembled context produced by ``ContextBuilder.build``.

    Attributes:
        current_question: The trimmed, validated question being asked now.
        history_messages: Ordered (oldest → newest) slice of conversation
            history that was actually included in ``context_query``.
        context_query: The formatted string ready to pass to the RAG service
            as the enriched query.
        message_count: Number of history messages included.
        was_truncated: ``True`` when the character limit caused one or more
            of the oldest messages to be dropped from the window.
    """

    current_question: str
    history_messages: list[Message] = field(default_factory=list)
    context_query: str = ""
    message_count: int = 0
    was_truncated: bool = False


# ---------------------------------------------------------------------------
# ContextBuilder
# ---------------------------------------------------------------------------


class ContextBuilder:
    """Assembles a context-aware query from recent messages.

    All public methods are static — no instance is required.

    Responsibilities:
    - Accept a window of recent messages (oldest-to-newest).
    - Apply the character limit by dropping oldest messages when necessary.
    - Format the remaining history and current question into ``context_query``.
    - Return an immutable ``ConversationContext`` result.

    Out of scope:
    - Database access — messages are provided by the caller.
    - LLM or AI summarisation.
    - Retrieval or answer generation.
    - Pagination or lazy loading.
    """

    @staticmethod
    def build(
        current_question: str,
        recent_messages: list[Message],
        *,
        max_chars: int = MAX_CONTEXT_CHARACTERS,
    ) -> ConversationContext:
        """Assemble a ``ConversationContext`` from *recent_messages*.

        Processing steps:
        1. Apply the character limit against the fully formatted
           ``context_query``: drop the oldest messages first, then truncate
           the question text only if still over the limit.
        2. Format the retained messages and question into a deterministic
           plain-text ``context_query``.
        3. Return a ``ConversationContext`` capturing all of the above.

        Args:
            current_question: The trimmed current question (must be non-empty;
                callers are responsible for validation).
            recent_messages: Candidate history messages ordered
                oldest-to-newest.  The caller controls the window size;
                this method only enforces the character limit.
            max_chars: Maximum length of the assembled ``context_query``.
                Defaults to ``MAX_CONTEXT_CHARACTERS``.

        Returns:
            A ``ConversationContext`` with the assembled query.
        """
        if max_chars <= 0:
            return ConversationContext(
                current_question=current_question,
                history_messages=[],
                context_query="",
                message_count=0,
                was_truncated=True,
            )

        trimmed, question_for_query, was_truncated = ContextBuilder._apply_char_limit(
            recent_messages,
            current_question,
            max_chars,
        )
        context_query = ContextBuilder._format_context_query(
            trimmed, question_for_query
        )

        return ConversationContext(
            current_question=current_question,
            history_messages=trimmed,
            context_query=context_query,
            message_count=len(trimmed),
            was_truncated=was_truncated,
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _apply_char_limit(
        messages: list[Message],
        current_question: str,
        max_chars: int,
    ) -> tuple[list[Message], str, bool]:
        """Fit the assembled context string within *max_chars*.

        Truncation order:
        1. Drop the oldest history messages while the formatted query exceeds
           the limit.
        2. If still over the limit, truncate *current_question* from the end.

        The result always preserves chronological order within retained
        messages.  ``ConversationContext.current_question`` remains the full
        input question; only the formatted query may use a truncated copy.

        Args:
            messages: Candidate messages ordered oldest-to-newest.
            current_question: The current question to include in the query.
            max_chars: Maximum length of the assembled ``context_query``.

        Returns:
            A 3-tuple ``(retained_messages, question_for_query, was_truncated)``.
        """
        if max_chars <= 0:
            return [], "", True

        window = list(messages)
        was_truncated = False

        while (
            window
            and len(
                ContextBuilder._format_context_query(window, current_question)
            )
            > max_chars
        ):
            window.pop(0)
            was_truncated = True

        question_for_query = current_question
        if (
            len(
                ContextBuilder._format_context_query(window, question_for_query)
            )
            > max_chars
        ):
            question_for_query = ContextBuilder._truncate_question(
                window,
                current_question,
                max_chars,
            )
            was_truncated = True

        return window, question_for_query, was_truncated

    @staticmethod
    def _truncate_question(
        messages: list[Message],
        question: str,
        max_chars: int,
    ) -> str:
        """Return the longest prefix of *question* that fits in *max_chars*.

        Args:
            messages: History messages already selected for the context window.
            question: Full current question text.
            max_chars: Maximum allowed length of the formatted query.

        Returns:
            A (possibly empty) prefix of *question*.
        """
        overhead = len(ContextBuilder._format_context_query(messages, ""))
        max_question_len = max(0, max_chars - overhead)
        return question[:max_question_len]

    @staticmethod
    def _format_context_query(
        messages: list[Message],
        current_question: str,
    ) -> str:
        """Build the formatted context string.

        Format when history is non-empty::

            Conversation context:
            User: <content>
            Assistant: <content>
            ...

            Current question: <current_question>

        Format when history is empty::

            Current question: <current_question>

        The output is deterministic for identical inputs.

        Args:
            messages: History messages, oldest-to-newest.
            current_question: The current question to append.

        Returns:
            Formatted plain-text context string.
        """
        if not messages:
            return f"{_CURRENT_QUESTION_PREFIX} {current_question}"

        lines: list[str] = [_CONTEXT_HEADER]
        for msg in messages:
            label = _ROLE_LABELS.get(msg.role, _UNKNOWN_ROLE_LABEL)
            lines.append(f"{label}: {msg.content}")

        lines.append("")  # blank separator line
        lines.append(f"{_CURRENT_QUESTION_PREFIX} {current_question}")
        return "\n".join(lines)

    @staticmethod
    def format_history(messages: list[Message]) -> str | None:
        """Format prior conversation turns for LLM prompt injection only.

        Retrieval must use ``current_question`` — not this formatted history.
        """
        if not messages:
            return None

        lines: list[str] = [_CONTEXT_HEADER]
        for msg in messages:
            label = _ROLE_LABELS.get(msg.role, _UNKNOWN_ROLE_LABEL)
            lines.append(f"{label}: {msg.content}")
        return "\n".join(lines)
