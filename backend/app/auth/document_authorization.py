"""Document-level authorization service (Phase 5.4).

Determines whether a specific user may perform an action on a specific
document, using the security metadata fields introduced in Phase 5.2:

    - ``visibility``    — PUBLIC / RESTRICTED / PRIVATE
    - ``owner_id``      — document owner UUID
    - ``allowed_roles`` — role names permitted when RESTRICTED

All evaluation is performed here.  Routes must not implement their own
authorization logic for individual documents.

The service is purposely stateless — every public method accepts both
``user`` and ``document`` as parameters and returns a plain
``DocumentAccessDecision``.  This makes the logic easy to unit-test in
complete isolation from FastAPI and SQLAlchemy.

Architecture note
-----------------
* Does NOT depend on ``FastAPI``, ``Session``, or any route layer.
* Does NOT modify the ``Document`` model or its stored metadata.
* Role normalization (``normalize_allowed_roles``) is performed here
  so the ``Document`` model remains a passive data container.
* Admin shortcut is evaluated first so all other checks can assume
  non-admin users.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto

from app.auth.dependencies import (
    get_user_system_roles,
    normalize_allowed_roles,
)
from app.auth.role_permissions import SystemRole
from app.db.models.document import Document
from app.db.models.user import User
from app.documents.visibility import DocumentVisibility, resolve_visibility


class AccessOutcome(Enum):
    """Outcome values for a document access decision."""

    GRANTED = auto()
    DENIED_VISIBILITY = auto()
    DENIED_ROLE = auto()
    DENIED_PRIVATE = auto()
    DENIED_UNKNOWN_VISIBILITY = auto()


@dataclass(frozen=True)
class DocumentAccessDecision:
    """Immutable result of a document access check.

    Attributes:
        granted: ``True`` when access is permitted.
        outcome: Specific outcome code for the decision.
        reason: Human-readable explanation (used for logging).
        document_id: UUID of the evaluated document.
        user_id: UUID of the requesting user.
    """

    granted: bool
    outcome: AccessOutcome
    reason: str
    document_id: uuid.UUID
    user_id: uuid.UUID


class DocumentAuthorizationService:
    """Evaluate whether a user may access a specific document.

    All methods are stateless.  Callers pass ``user`` and ``document``
    objects that have already been loaded from the database.

    Authorization hierarchy (evaluated in order):
    1. Admin role   → always granted.
    2. Owner        → always granted.
    3. visibility = PUBLIC     → granted to any authenticated user.
    4. visibility = RESTRICTED → granted if user role is in allowed_roles.
    5. visibility = PRIVATE    → denied (owner/admin already granted above).
    6. Unknown visibility      → denied securely.
    """

    # --------------------------------------------------------------------- #
    # Public API                                                              #
    # --------------------------------------------------------------------- #

    @staticmethod
    def can_read_document(user: User, document: Document) -> DocumentAccessDecision:
        """Return whether *user* may read *document* metadata and content.

        Args:
            user: Authenticated requesting user.
            document: The document being accessed.

        Returns:
            ``DocumentAccessDecision`` with ``granted=True`` when access is
            permitted.
        """
        return DocumentAuthorizationService._evaluate(user, document, action="read")

    @staticmethod
    def can_update_document(user: User, document: Document) -> DocumentAccessDecision:
        """Return whether *user* may update *document*.

        Owners may update their own documents (future support).
        Admins always have access.

        Args:
            user: Authenticated requesting user.
            document: The document being modified.

        Returns:
            ``DocumentAccessDecision`` describing the authorization outcome.
        """
        return DocumentAuthorizationService._evaluate(user, document, action="update")

    @staticmethod
    def can_delete_document(user: User, document: Document) -> DocumentAccessDecision:
        """Return whether *user* may delete *document*.

        Args:
            user: Authenticated requesting user.
            document: The document to be deleted.

        Returns:
            ``DocumentAccessDecision`` describing the authorization outcome.
        """
        return DocumentAuthorizationService._evaluate(user, document, action="delete")

    @staticmethod
    def can_manage_document(user: User, document: Document) -> DocumentAccessDecision:
        """Return whether *user* may perform management actions on *document*.

        Management encompasses ownership reassignment, metadata edits, and
        visibility changes.  Reserved for owners and admins.

        Args:
            user: Authenticated requesting user.
            document: The document being managed.

        Returns:
            ``DocumentAccessDecision`` describing the authorization outcome.
        """
        return DocumentAuthorizationService._evaluate(user, document, action="manage")

    # --------------------------------------------------------------------- #
    # Core evaluation logic                                                   #
    # --------------------------------------------------------------------- #

    @staticmethod
    def _evaluate(
        user: User,
        document: Document,
        *,
        action: str,
    ) -> DocumentAccessDecision:
        """Evaluate document access for *user* performing *action*.

        Evaluation order:
        1. Admin shortcut.
        2. Owner shortcut.
        3. Visibility-based rules.

        Args:
            user: Authenticated requesting user.
            document: Document being accessed.
            action: Descriptive action label for logging.

        Returns:
            Immutable ``DocumentAccessDecision``.
        """
        doc_id = document.id
        user_id = user.id
        user_roles = get_user_system_roles(user)

        # 1. Admin always has access.
        if SystemRole.ADMIN in user_roles:
            return DocumentAccessDecision(
                granted=True,
                outcome=AccessOutcome.GRANTED,
                reason="admin",
                document_id=doc_id,
                user_id=user_id,
            )

        # 2. Owner always has access to their own document.
        if document.owner_id is not None and document.owner_id == user.id:
            return DocumentAccessDecision(
                granted=True,
                outcome=AccessOutcome.GRANTED,
                reason="owner",
                document_id=doc_id,
                user_id=user_id,
            )

        # 3. Resolve visibility — fail securely on unknown values.
        visibility = resolve_visibility(document.visibility)
        if visibility is None:
            return DocumentAccessDecision(
                granted=False,
                outcome=AccessOutcome.DENIED_UNKNOWN_VISIBILITY,
                reason=f"unknown visibility '{document.visibility}'",
                document_id=doc_id,
                user_id=user_id,
            )

        # 4. PUBLIC — any authenticated user is allowed.
        if visibility == DocumentVisibility.PUBLIC:
            return DocumentAccessDecision(
                granted=True,
                outcome=AccessOutcome.GRANTED,
                reason="public visibility",
                document_id=doc_id,
                user_id=user_id,
            )

        # 5. PRIVATE — only owner/admin (already handled above).
        if visibility == DocumentVisibility.PRIVATE:
            return DocumentAccessDecision(
                granted=False,
                outcome=AccessOutcome.DENIED_PRIVATE,
                reason="private document — owner or admin required",
                document_id=doc_id,
                user_id=user_id,
            )

        # 6. RESTRICTED — user must have at least one allowed role.
        if visibility == DocumentVisibility.RESTRICTED:
            allowed = normalize_allowed_roles(document.allowed_roles)

            if not allowed:
                # No valid roles in the list → treat as inaccessible.
                return DocumentAccessDecision(
                    granted=False,
                    outcome=AccessOutcome.DENIED_ROLE,
                    reason="restricted document with no valid allowed roles",
                    document_id=doc_id,
                    user_id=user_id,
                )

            if user_roles & allowed:
                return DocumentAccessDecision(
                    granted=True,
                    outcome=AccessOutcome.GRANTED,
                    reason="role in allowed_roles",
                    document_id=doc_id,
                    user_id=user_id,
                )

            return DocumentAccessDecision(
                granted=False,
                outcome=AccessOutcome.DENIED_ROLE,
                reason="user role not in allowed_roles",
                document_id=doc_id,
                user_id=user_id,
            )

        # Fallback — no rule matched; fail securely.
        return DocumentAccessDecision(
            granted=False,
            outcome=AccessOutcome.DENIED_UNKNOWN_VISIBILITY,
            reason=f"unhandled visibility '{visibility}'",
            document_id=doc_id,
            user_id=user_id,
        )


def log_document_access_denied(
    *,
    decision: DocumentAccessDecision,
    user: User,
    endpoint: str,
) -> None:
    """Emit a structured audit event for a denied document access decision.

    Delegates to ``AuditService`` so that all security events pass through
    the centralised audit pipeline rather than writing to the logger directly.

    Args:
        decision: The ``DocumentAccessDecision`` that was denied.
        user: The requesting user (used for identifier fields).
        endpoint: The HTTP route path for audit context.
    """
    from app.audit.service import AuditService

    AuditService.record(
        AuditService.document_access_denied(
            user_id=str(decision.user_id),
            username=user.username or user.email,
            document_id=str(decision.document_id),
            action="read",
            reason=decision.reason,
            endpoint=endpoint,
        )
    )
