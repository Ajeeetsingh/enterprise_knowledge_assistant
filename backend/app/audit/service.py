"""AuditService — centralized audit event recording (Phase 5.6).

All audit logging in the application must pass through this service.
No other module should write audit log lines directly.

Architecture principles
-----------------------
* ``AuditService`` is stateless.  All public methods are ``@staticmethod``.
* ``AuditService`` never contains authorization logic.  It only receives
  pre-made decisions and records them.
* ``AuditService.record()`` is failure-safe: it swallows all internal
  exceptions so that an audit-logging bug can never crash the application.
* Factory methods construct ``AuditEvent`` objects for every supported
  event type; callers import only the factory they need.
* Logging is performed with the existing ``log_with_fields()`` infrastructure,
  which is compatible with ELK, Splunk, Azure Monitor, CloudWatch, and
  Datadog ingestion pipelines.

Sensitive-data rules (never included in any audit event)
---------------------------------------------------------
- Passwords or password hashes
- JWT access or refresh tokens
- Document contents or uploaded file bytes
- Vector embeddings
- LLM prompts or generated responses
"""

from __future__ import annotations

import logging
from typing import Any

from app.audit.events import (
    AuditEvent,
    AuditEventType,
    AuditOutcome,
    build_event,
)
from app.core.logging import get_logger, log_with_fields

_audit_logger = get_logger("app.audit")

# Log level per outcome for structured SIEM filtering.
_OUTCOME_LEVEL: dict[AuditOutcome, int] = {
    AuditOutcome.SUCCESS: logging.INFO,
    AuditOutcome.GRANTED: logging.INFO,
    AuditOutcome.DENIED: logging.WARNING,
    AuditOutcome.FAILURE: logging.WARNING,
}


class AuditService:
    """Centralized audit event creation and structured logging.

    Usage::

        event = AuditService.login_success(email="user@example.com")
        AuditService.record(event)

    All factory methods return an ``AuditEvent`` ready for ``record()``.
    Callers may enrich the event before recording it (e.g. adding
    ``request_id`` or ``ip_address``) by calling ``dataclasses.replace()``.
    """

    # ------------------------------------------------------------------ #
    # Core recording                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def record(event: AuditEvent) -> None:
        """Write *event* to the structured audit log.

        This method is **failure-safe**: any internal exception is caught,
        logged to the application logger, and silently discarded so that
        audit-logging failures never affect application behaviour.

        Args:
            event: The ``AuditEvent`` to record.
        """
        try:
            level = _OUTCOME_LEVEL.get(event.outcome, logging.INFO)
            fields: dict[str, Any] = {
                "event_id": str(event.event_id),
                "event_type": str(event.event_type),
                "action": event.action,
                "resource_type": event.resource_type,
                "outcome": str(event.outcome),
                "timestamp": event.timestamp.isoformat(),
            }
            if event.user_id is not None:
                fields["user_id"] = event.user_id
            if event.username is not None:
                fields["username"] = event.username
            if event.resource_id is not None:
                fields["resource_id"] = event.resource_id
            if event.reason is not None:
                fields["reason"] = event.reason
            if event.request_id is not None:
                fields["request_id"] = event.request_id
            if event.ip_address is not None:
                fields["ip_address"] = event.ip_address
            if event.user_agent is not None:
                fields["user_agent"] = event.user_agent
            if event.metadata:
                for k, v in event.metadata.items():
                    fields[f"meta_{k}"] = v

            log_with_fields(_audit_logger, level, "AUDIT", **fields)
        except Exception as exc:  # pragma: no cover — safety net
            logging.getLogger(__name__).warning(
                "Audit logging failed — event not recorded: %s",
                type(exc).__name__,
            )

    # ------------------------------------------------------------------ #
    # Authentication factory methods                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def login_success(
        *,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a login-success audit event.

        Args:
            email: The email address that authenticated successfully.
            ip_address: Client IP address, if available.
            user_agent: HTTP User-Agent header, if available.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=AUTH_LOGIN_SUCCESS``.
        """
        return build_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            action="login",
            resource_type="session",
            outcome=AuditOutcome.SUCCESS,
            username=email,
            reason="credentials valid",
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def login_failure(
        *,
        email: str,
        reason: str = "invalid credentials",
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a login-failure audit event.

        Args:
            email: The email address that failed to authenticate.
            reason: Human-readable failure reason (never include the password).
            ip_address: Client IP address, if available.
            user_agent: HTTP User-Agent header, if available.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=AUTH_LOGIN_FAILURE``.
        """
        return build_event(
            event_type=AuditEventType.AUTH_LOGIN_FAILURE,
            action="login",
            resource_type="session",
            outcome=AuditOutcome.FAILURE,
            username=email,
            reason=reason,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def logout(
        *,
        request_id: str | None = None,
        ip_address: str | None = None,
    ) -> AuditEvent:
        """Build a logout audit event (stateless — no user context).

        Args:
            request_id: Optional trace identifier.
            ip_address: Client IP address, if available.

        Returns:
            ``AuditEvent`` with ``event_type=AUTH_LOGOUT``.
        """
        return build_event(
            event_type=AuditEventType.AUTH_LOGOUT,
            action="logout",
            resource_type="session",
            outcome=AuditOutcome.SUCCESS,
            request_id=request_id,
            ip_address=ip_address,
        )

    # ------------------------------------------------------------------ #
    # Authorization factory methods                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def permission_denied(
        *,
        user_id: str,
        username: str,
        permission: str,
        endpoint: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a permission-denied audit event for route-level authorization.

        Args:
            user_id: String UUID of the user whose request was denied.
            username: Email or username for human-readable identification.
            permission: The permission or role value that was required.
            endpoint: HTTP route path (e.g. ``"/api/v1/documents/upload"``).
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=AUTHZ_PERMISSION_DENIED``.
        """
        return build_event(
            event_type=AuditEventType.AUTHZ_PERMISSION_DENIED,
            action="permission_check",
            resource_type="endpoint",
            outcome=AuditOutcome.DENIED,
            user_id=user_id,
            username=username,
            resource_id=endpoint,
            reason=f"required: {permission}",
            request_id=request_id,
        )

    # ------------------------------------------------------------------ #
    # Document access factory methods                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def document_access_denied(
        *,
        user_id: str,
        username: str,
        document_id: str,
        action: str,
        reason: str,
        endpoint: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a document-access-denied audit event.

        Args:
            user_id: String UUID of the requesting user.
            username: Email or username.
            document_id: String UUID of the document.
            action: The action that was denied (``"read"``, ``"delete"``, …).
            reason: Authorization decision reason from
                ``DocumentAccessDecision.reason``.
            endpoint: HTTP route path.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=DOCUMENT_ACCESS_DENIED``.
        """
        return build_event(
            event_type=AuditEventType.DOCUMENT_ACCESS_DENIED,
            action=action,
            resource_type="document",
            outcome=AuditOutcome.DENIED,
            user_id=user_id,
            username=username,
            resource_id=document_id,
            reason=reason,
            request_id=request_id,
            metadata={"endpoint": endpoint},
        )

    @staticmethod
    def document_read(
        *,
        user_id: str,
        document_id: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a document-read audit event.

        Args:
            user_id: String UUID of the user reading the document.
            document_id: String UUID of the document.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=DOCUMENT_READ``.
        """
        return build_event(
            event_type=AuditEventType.DOCUMENT_READ,
            action="read",
            resource_type="document",
            outcome=AuditOutcome.SUCCESS,
            user_id=user_id,
            resource_id=document_id,
            request_id=request_id,
        )

    @staticmethod
    def document_created(
        *,
        user_id: str,
        document_id: str,
        filename: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a document-upload audit event.

        Args:
            user_id: String UUID of the uploading user.
            document_id: String UUID of the newly created document.
            filename: Original filename (never include file contents).
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=DOCUMENT_CREATE``.
        """
        return build_event(
            event_type=AuditEventType.DOCUMENT_CREATE,
            action="upload",
            resource_type="document",
            outcome=AuditOutcome.SUCCESS,
            user_id=user_id,
            resource_id=document_id,
            metadata={"filename": filename},
            request_id=request_id,
        )

    @staticmethod
    def document_deleted(
        *,
        user_id: str,
        document_id: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a document-delete audit event.

        Args:
            user_id: String UUID of the user deleting the document.
            document_id: String UUID of the deleted document.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=DOCUMENT_DELETE``.
        """
        return build_event(
            event_type=AuditEventType.DOCUMENT_DELETE,
            action="delete",
            resource_type="document",
            outcome=AuditOutcome.SUCCESS,
            user_id=user_id,
            resource_id=document_id,
            request_id=request_id,
        )

    # ------------------------------------------------------------------ #
    # RAG factory methods                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def rag_query(
        *,
        user_id: str,
        query_id: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a RAG-query-executed audit event.

        Args:
            user_id: String UUID of the user submitting the query.
            query_id: Unique identifier for this RAG query.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=RAG_QUERY``.
        """
        return build_event(
            event_type=AuditEventType.RAG_QUERY,
            action="query",
            resource_type="rag_query",
            outcome=AuditOutcome.SUCCESS,
            user_id=user_id,
            resource_id=query_id,
            request_id=request_id,
        )

    @staticmethod
    def rag_retrieval_filtered(
        *,
        user_id: str,
        query_id: str | None,
        candidate_count: int,
        authorized_count: int,
        filtered_count: int,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a RAG-retrieval-filtered audit event.

        Emitted whenever the retrieval authorization layer removes documents
        from the candidate set.  Only emitted when ``filtered_count > 0``.

        Args:
            user_id: String UUID of the requesting user.
            query_id: Unique identifier for the RAG query.
            candidate_count: Total documents before authorization.
            authorized_count: Documents retained after authorization.
            filtered_count: Documents removed by authorization.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=RAG_RETRIEVAL_FILTERED``.
        """
        return build_event(
            event_type=AuditEventType.RAG_RETRIEVAL_FILTERED,
            action="retrieval_filter",
            resource_type="rag_query",
            outcome=AuditOutcome.DENIED,
            user_id=user_id,
            resource_id=query_id,
            reason=f"{filtered_count} document(s) filtered by authorization",
            request_id=request_id,
            metadata={
                "candidate_count": candidate_count,
                "authorized_count": authorized_count,
                "filtered_count": filtered_count,
            },
        )

    # ------------------------------------------------------------------ #
    # Administration factory methods                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def user_created(
        *,
        admin_id: str,
        admin_username: str,
        target_user_id: str,
        target_email: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a user-created audit event.

        Args:
            admin_id: String UUID of the admin performing the action.
            admin_username: Email or username of the admin.
            target_user_id: String UUID of the newly created user.
            target_email: Email of the newly created user.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=ADMIN_USER_CREATED``.
        """
        return build_event(
            event_type=AuditEventType.ADMIN_USER_CREATED,
            action="create_user",
            resource_type="user",
            outcome=AuditOutcome.SUCCESS,
            user_id=admin_id,
            username=admin_username,
            resource_id=target_user_id,
            metadata={"target_email": target_email},
            request_id=request_id,
        )

    @staticmethod
    def user_updated(
        *,
        admin_id: str,
        admin_username: str,
        target_user_id: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a user-updated audit event.

        Args:
            admin_id: String UUID of the admin performing the action.
            admin_username: Email or username of the admin.
            target_user_id: String UUID of the updated user.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=ADMIN_USER_UPDATED``.
        """
        return build_event(
            event_type=AuditEventType.ADMIN_USER_UPDATED,
            action="update_user",
            resource_type="user",
            outcome=AuditOutcome.SUCCESS,
            user_id=admin_id,
            username=admin_username,
            resource_id=target_user_id,
            request_id=request_id,
        )

    @staticmethod
    def user_deleted(
        *,
        admin_id: str,
        admin_username: str,
        target_user_id: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a user-deleted audit event.

        Args:
            admin_id: String UUID of the admin performing the action.
            admin_username: Email or username of the admin.
            target_user_id: String UUID of the deleted user.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=ADMIN_USER_DELETED``.
        """
        return build_event(
            event_type=AuditEventType.ADMIN_USER_DELETED,
            action="delete_user",
            resource_type="user",
            outcome=AuditOutcome.SUCCESS,
            user_id=admin_id,
            username=admin_username,
            resource_id=target_user_id,
            request_id=request_id,
        )

    @staticmethod
    def role_assigned(
        *,
        admin_id: str,
        admin_username: str,
        target_user_id: str,
        role_names: list[str],
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a role-assigned audit event.

        Args:
            admin_id: String UUID of the admin performing the action.
            admin_username: Email or username of the admin.
            target_user_id: String UUID of the user receiving the roles.
            role_names: Names of the roles being assigned.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=ADMIN_ROLE_ASSIGNED``.
        """
        return build_event(
            event_type=AuditEventType.ADMIN_ROLE_ASSIGNED,
            action="assign_roles",
            resource_type="role",
            outcome=AuditOutcome.SUCCESS,
            user_id=admin_id,
            username=admin_username,
            resource_id=target_user_id,
            metadata={"role_names": ",".join(sorted(role_names))},
            request_id=request_id,
        )

    @staticmethod
    def role_removed(
        *,
        admin_id: str,
        admin_username: str,
        target_user_id: str,
        role_name: str,
        request_id: str | None = None,
    ) -> AuditEvent:
        """Build a role-removed audit event.

        Args:
            admin_id: String UUID of the admin performing the action.
            admin_username: Email or username of the admin.
            target_user_id: String UUID of the user whose role was removed.
            role_name: Name of the role that was removed.
            request_id: Optional trace identifier.

        Returns:
            ``AuditEvent`` with ``event_type=ADMIN_ROLE_REMOVED``.
        """
        return build_event(
            event_type=AuditEventType.ADMIN_ROLE_REMOVED,
            action="remove_role",
            resource_type="role",
            outcome=AuditOutcome.SUCCESS,
            user_id=admin_id,
            username=admin_username,
            resource_id=target_user_id,
            metadata={"role_name": role_name},
            request_id=request_id,
        )
