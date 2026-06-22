"""Audit event model for Phase 5.6 — enterprise audit logging.

Defines the canonical ``AuditEvent`` dataclass together with the
``AuditEventType`` and ``AuditOutcome`` enumerations that describe every
security-sensitive action in the system.

Design goals
------------
* Immutable — ``AuditEvent`` is a frozen dataclass; fields are never mutated
  after construction.
* Future-proof — the ``metadata`` dict accepts arbitrary key/value pairs so
  additional context can be captured without schema changes.
* SIEM-ready — field names are stable identifiers suitable for indexing in
  ELK, Splunk, Azure Monitor, CloudWatch, and Datadog.
* Sensitive-data-free — passwords, tokens, document contents, embeddings,
  LLM prompts/responses, and uploaded file bytes are NEVER included.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]
        pass


class AuditEventType(StrEnum):
    """Canonical identifiers for every auditable security event.

    Format: ``<domain>.<sub-domain>.<verb>``.
    New events should follow the same dotted-path convention so log routers
    can filter by prefix (e.g. ``event_type=auth.*``).
    """

    # ---------------------------------------------------------------------- #
    # Authentication                                                           #
    # ---------------------------------------------------------------------- #
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"

    # ---------------------------------------------------------------------- #
    # Authorization (route-level)                                             #
    # ---------------------------------------------------------------------- #
    AUTHZ_PERMISSION_GRANTED = "authz.permission.granted"
    AUTHZ_PERMISSION_DENIED = "authz.permission.denied"

    # ---------------------------------------------------------------------- #
    # Document operations                                                      #
    # ---------------------------------------------------------------------- #
    DOCUMENT_READ = "document.read"
    DOCUMENT_CREATE = "document.create"
    DOCUMENT_UPDATE = "document.update"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_ACCESS_DENIED = "document.access.denied"

    # ---------------------------------------------------------------------- #
    # RAG retrieval                                                           #
    # ---------------------------------------------------------------------- #
    RAG_QUERY = "rag.query"
    RAG_RETRIEVAL_FILTERED = "rag.retrieval.filtered"

    # ---------------------------------------------------------------------- #
    # Administration                                                          #
    # ---------------------------------------------------------------------- #
    ADMIN_USER_CREATED = "admin.user.created"
    ADMIN_USER_UPDATED = "admin.user.updated"
    ADMIN_USER_DELETED = "admin.user.deleted"
    ADMIN_ROLE_ASSIGNED = "admin.role.assigned"
    ADMIN_ROLE_REMOVED = "admin.role.removed"


class AuditOutcome(StrEnum):
    """Possible outcomes of an audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
    GRANTED = "granted"
    DENIED = "denied"


@dataclass(frozen=True)
class AuditEvent:
    """An immutable, structured record of one security-sensitive action.

    All optional fields default to ``None``; callers should populate as many
    as are contextually available.  The ``metadata`` dict is reserved for
    domain-specific supplementary data that does not fit into the fixed
    schema fields.

    Never store in this object:
    - passwords or password hashes
    - JWT tokens or refresh tokens
    - document contents or uploaded file bytes
    - vector embeddings
    - LLM prompts or generated responses

    Attributes:
        event_id: Unique event identifier (auto-generated UUID v4).
        timestamp: UTC datetime of the event (auto-generated).
        event_type: Canonical event type from ``AuditEventType``.
        action: Short human-readable description of the action taken.
        resource_type: Domain noun for the resource (e.g. ``"document"``,
            ``"user"``, ``"session"``, ``"rag_query"``).
        outcome: Result classification from ``AuditOutcome``.
        user_id: String UUID of the acting user; ``None`` for anonymous
            events such as failed logins with unknown email.
        username: Email or username of the acting user.
        resource_id: String identifier of the affected resource.
        reason: Human-readable explanation of the outcome.
        request_id: Correlates this event to an HTTP request trace.
        ip_address: Client IP address, if available from the request.
        user_agent: HTTP ``User-Agent`` header, if available.
        metadata: Arbitrary supplementary key/value pairs.
    """

    event_id: uuid.UUID
    timestamp: datetime
    event_type: AuditEventType
    action: str
    resource_type: str
    outcome: AuditOutcome
    user_id: str | None = None
    username: str | None = None
    resource_id: str | None = None
    reason: str | None = None
    request_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] | None = None


def _new_event_id() -> uuid.UUID:
    return uuid.uuid4()


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def build_event(
    *,
    event_type: AuditEventType,
    action: str,
    resource_type: str,
    outcome: AuditOutcome,
    user_id: str | None = None,
    username: str | None = None,
    resource_id: str | None = None,
    reason: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Construct an ``AuditEvent`` with auto-generated ``event_id`` and
    ``timestamp``.

    This is the canonical factory used by ``AuditService`` helper methods.
    Callers outside the audit module should prefer ``AuditService`` methods.

    Args:
        event_type: Canonical event type.
        action: Short description of the action.
        resource_type: Domain noun for the affected resource.
        outcome: Outcome classification.
        user_id: String UUID of the acting user.
        username: Email or username of the acting user.
        resource_id: Identifier of the affected resource.
        reason: Human-readable outcome explanation.
        request_id: Optional HTTP request trace identifier.
        ip_address: Client IP, if available.
        user_agent: HTTP User-Agent, if available.
        metadata: Supplementary context.

    Returns:
        Immutable ``AuditEvent`` ready for ``AuditService.record()``.
    """
    return AuditEvent(
        event_id=_new_event_id(),
        timestamp=_utc_now(),
        event_type=event_type,
        action=action,
        resource_type=resource_type,
        outcome=outcome,
        user_id=user_id,
        username=username,
        resource_id=resource_id,
        reason=reason,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata,
    )
