"""Document visibility levels for the access control model.

Visibility is the first axis of document authorization.  It determines
who may *discover* a document before role or ownership checks apply.
Future phases layer ownership and role filters on top of this value.
"""

from __future__ import annotations

from enum import StrEnum


class DocumentVisibility(StrEnum):
    """Controls the default audience of a document.

    Values are stored as plain strings in the ``documents`` table so that
    the column remains portable across PostgreSQL and SQLite without a
    native enum type.

    Attributes:
        PUBLIC: Visible to any authenticated user regardless of role.
            Appropriate for company-wide policies and announcements.
        RESTRICTED: Visible only to users whose role appears in the
            document's ``allowed_roles`` list.  This is the default for
            most enterprise documents.
        PRIVATE: Visible only to the document owner (``owner_id``).
            Intended for personal drafts or sensitive personal records.
    """

    PUBLIC = "public"
    RESTRICTED = "restricted"
    PRIVATE = "private"


# Default applied to newly uploaded documents when no visibility is specified.
DEFAULT_VISIBILITY: DocumentVisibility = DocumentVisibility.RESTRICTED


def resolve_visibility(
    value: str | DocumentVisibility | None,
) -> DocumentVisibility | None:
    """Resolve an arbitrary value to a ``DocumentVisibility`` member.

    Args:
        value: A raw string, enum member, or ``None``.

    Returns:
        The matching ``DocumentVisibility``, or ``None`` when *value* is
        unknown, empty, or an unsupported type.
    """
    if value is None:
        return None
    if isinstance(value, DocumentVisibility):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    for member in DocumentVisibility:
        if normalized == member.value:
            return member
    return None
