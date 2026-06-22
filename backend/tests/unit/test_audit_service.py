"""Unit tests for Phase 5.6 — AuditService and AuditEvent model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.audit.events import (
    AuditEvent,
    AuditEventType,
    AuditOutcome,
    build_event,
)
from app.audit.service import AuditService


# ---------------------------------------------------------------------------
# build_event / AuditEvent
# ---------------------------------------------------------------------------

class TestAuditEventModel:
    def test_build_event_sets_event_id_and_timestamp(self) -> None:
        event = build_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            action="login",
            resource_type="session",
            outcome=AuditOutcome.SUCCESS,
        )
        assert isinstance(event.event_id, uuid.UUID)
        assert isinstance(event.timestamp, datetime)
        assert event.timestamp.tzinfo is not None

    def test_build_event_required_fields(self) -> None:
        event = build_event(
            event_type=AuditEventType.AUTHZ_PERMISSION_DENIED,
            action="permission_check",
            resource_type="endpoint",
            outcome=AuditOutcome.DENIED,
        )
        assert event.event_type == AuditEventType.AUTHZ_PERMISSION_DENIED
        assert event.action == "permission_check"
        assert event.resource_type == "endpoint"
        assert event.outcome == AuditOutcome.DENIED

    def test_build_event_optional_fields_default_to_none(self) -> None:
        event = build_event(
            event_type=AuditEventType.AUTH_LOGOUT,
            action="logout",
            resource_type="session",
            outcome=AuditOutcome.SUCCESS,
        )
        assert event.user_id is None
        assert event.username is None
        assert event.resource_id is None
        assert event.reason is None
        assert event.request_id is None
        assert event.ip_address is None
        assert event.user_agent is None
        assert event.metadata is None

    def test_build_event_optional_fields_populated(self) -> None:
        meta = {"extra": "value"}
        event = build_event(
            event_type=AuditEventType.DOCUMENT_READ,
            action="read",
            resource_type="document",
            outcome=AuditOutcome.SUCCESS,
            user_id="uid-123",
            username="alice@example.com",
            resource_id="doc-456",
            reason="public visibility",
            request_id="req-789",
            ip_address="192.0.2.1",
            user_agent="Mozilla/5.0",
            metadata=meta,
        )
        assert event.user_id == "uid-123"
        assert event.username == "alice@example.com"
        assert event.resource_id == "doc-456"
        assert event.reason == "public visibility"
        assert event.request_id == "req-789"
        assert event.ip_address == "192.0.2.1"
        assert event.user_agent == "Mozilla/5.0"
        assert event.metadata == meta

    def test_audit_event_is_immutable(self) -> None:
        event = build_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            action="login",
            resource_type="session",
            outcome=AuditOutcome.SUCCESS,
        )
        with pytest.raises((AttributeError, TypeError)):
            event.user_id = "mutated"  # type: ignore[misc]

    def test_each_event_has_unique_id(self) -> None:
        a = build_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            action="login",
            resource_type="session",
            outcome=AuditOutcome.SUCCESS,
        )
        b = build_event(
            event_type=AuditEventType.AUTH_LOGIN_SUCCESS,
            action="login",
            resource_type="session",
            outcome=AuditOutcome.SUCCESS,
        )
        assert a.event_id != b.event_id

    def test_event_types_are_string_enum(self) -> None:
        assert str(AuditEventType.AUTH_LOGIN_SUCCESS) == "auth.login.success"
        assert str(AuditEventType.AUTHZ_PERMISSION_DENIED) == "authz.permission.denied"
        assert str(AuditEventType.DOCUMENT_ACCESS_DENIED) == "document.access.denied"
        assert str(AuditEventType.RAG_QUERY) == "rag.query"
        assert str(AuditEventType.ADMIN_USER_CREATED) == "admin.user.created"

    def test_outcomes_are_string_enum(self) -> None:
        assert str(AuditOutcome.SUCCESS) == "success"
        assert str(AuditOutcome.FAILURE) == "failure"
        assert str(AuditOutcome.GRANTED) == "granted"
        assert str(AuditOutcome.DENIED) == "denied"


# ---------------------------------------------------------------------------
# AuditService.record()
# ---------------------------------------------------------------------------

class TestAuditServiceRecord:
    def test_record_does_not_raise(self) -> None:
        event = AuditService.login_success(email="test@example.com")
        AuditService.record(event)  # should not raise

    def test_record_failure_safe(self) -> None:
        """record() must not raise even if the logger fails."""
        event = AuditService.login_success(email="x@example.com")
        with patch("app.audit.service.log_with_fields", side_effect=RuntimeError("boom")):
            AuditService.record(event)  # must not propagate the exception


# ---------------------------------------------------------------------------
# Authentication factory methods
# ---------------------------------------------------------------------------

class TestAuthFactoryMethods:
    def test_login_success(self) -> None:
        event = AuditService.login_success(email="user@example.com")
        assert event.event_type == AuditEventType.AUTH_LOGIN_SUCCESS
        assert event.outcome == AuditOutcome.SUCCESS
        assert event.username == "user@example.com"
        assert event.resource_type == "session"

    def test_login_success_with_context(self) -> None:
        event = AuditService.login_success(
            email="user@example.com",
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
            request_id="req-abc",
        )
        assert event.ip_address == "10.0.0.1"
        assert event.user_agent == "TestAgent/1.0"
        assert event.request_id == "req-abc"

    def test_login_failure(self) -> None:
        event = AuditService.login_failure(email="bad@example.com")
        assert event.event_type == AuditEventType.AUTH_LOGIN_FAILURE
        assert event.outcome == AuditOutcome.FAILURE
        assert event.username == "bad@example.com"

    def test_login_failure_custom_reason(self) -> None:
        event = AuditService.login_failure(
            email="x@example.com", reason="account inactive"
        )
        assert event.reason == "account inactive"

    def test_logout(self) -> None:
        event = AuditService.logout()
        assert event.event_type == AuditEventType.AUTH_LOGOUT
        assert event.outcome == AuditOutcome.SUCCESS
        assert event.user_id is None

    def test_sensitive_data_not_in_login_events(self) -> None:
        event = AuditService.login_success(email="user@example.com")
        serialized = str(event)
        assert "password" not in serialized.lower()
        assert "token" not in serialized.lower()


# ---------------------------------------------------------------------------
# Authorization factory methods
# ---------------------------------------------------------------------------

class TestAuthorizationFactoryMethods:
    def test_permission_denied(self) -> None:
        event = AuditService.permission_denied(
            user_id="uid-1",
            username="alice@example.com",
            permission="document:delete",
            endpoint="/api/v1/documents/123",
        )
        assert event.event_type == AuditEventType.AUTHZ_PERMISSION_DENIED
        assert event.outcome == AuditOutcome.DENIED
        assert event.user_id == "uid-1"
        assert event.username == "alice@example.com"
        assert "document:delete" in event.reason


# ---------------------------------------------------------------------------
# Document factory methods
# ---------------------------------------------------------------------------

class TestDocumentFactoryMethods:
    def test_document_access_denied(self) -> None:
        event = AuditService.document_access_denied(
            user_id="uid-1",
            username="alice",
            document_id="doc-999",
            action="read",
            reason="private document",
            endpoint="/api/v1/documents/999",
        )
        assert event.event_type == AuditEventType.DOCUMENT_ACCESS_DENIED
        assert event.outcome == AuditOutcome.DENIED
        assert event.resource_id == "doc-999"
        assert event.reason == "private document"

    def test_document_read(self) -> None:
        event = AuditService.document_read(user_id="uid-1", document_id="doc-1")
        assert event.event_type == AuditEventType.DOCUMENT_READ
        assert event.outcome == AuditOutcome.SUCCESS

    def test_document_created(self) -> None:
        event = AuditService.document_created(
            user_id="uid-1", document_id="doc-1", filename="report.pdf"
        )
        assert event.event_type == AuditEventType.DOCUMENT_CREATE
        assert event.outcome == AuditOutcome.SUCCESS
        assert event.metadata is not None
        assert event.metadata["filename"] == "report.pdf"
        assert "content" not in str(event)

    def test_document_deleted(self) -> None:
        event = AuditService.document_deleted(user_id="uid-1", document_id="doc-1")
        assert event.event_type == AuditEventType.DOCUMENT_DELETE
        assert event.outcome == AuditOutcome.SUCCESS


# ---------------------------------------------------------------------------
# RAG factory methods
# ---------------------------------------------------------------------------

class TestRagFactoryMethods:
    def test_rag_query(self) -> None:
        event = AuditService.rag_query(user_id="uid-1", query_id="qid-1")
        assert event.event_type == AuditEventType.RAG_QUERY
        assert event.outcome == AuditOutcome.SUCCESS
        assert event.resource_id == "qid-1"

    def test_rag_retrieval_filtered(self) -> None:
        event = AuditService.rag_retrieval_filtered(
            user_id="uid-1",
            query_id="qid-1",
            candidate_count=10,
            authorized_count=6,
            filtered_count=4,
        )
        assert event.event_type == AuditEventType.RAG_RETRIEVAL_FILTERED
        assert event.outcome == AuditOutcome.DENIED
        assert event.metadata is not None
        assert event.metadata["candidate_count"] == 10
        assert event.metadata["authorized_count"] == 6
        assert event.metadata["filtered_count"] == 4

    def test_rag_events_contain_no_query_content(self) -> None:
        event = AuditService.rag_query(user_id="uid-1", query_id="qid-1")
        serialized = str(event)
        assert "LLM" not in serialized
        assert "prompt" not in serialized.lower()


# ---------------------------------------------------------------------------
# Administration factory methods
# ---------------------------------------------------------------------------

class TestAdminFactoryMethods:
    def test_user_created(self) -> None:
        event = AuditService.user_created(
            admin_id="admin-1",
            admin_username="admin@example.com",
            target_user_id="user-99",
            target_email="newuser@example.com",
        )
        assert event.event_type == AuditEventType.ADMIN_USER_CREATED
        assert event.outcome == AuditOutcome.SUCCESS
        assert event.resource_id == "user-99"
        assert event.metadata is not None
        assert event.metadata["target_email"] == "newuser@example.com"

    def test_user_updated(self) -> None:
        event = AuditService.user_updated(
            admin_id="admin-1",
            admin_username="admin@example.com",
            target_user_id="user-99",
        )
        assert event.event_type == AuditEventType.ADMIN_USER_UPDATED
        assert event.outcome == AuditOutcome.SUCCESS

    def test_user_deleted(self) -> None:
        event = AuditService.user_deleted(
            admin_id="admin-1",
            admin_username="admin@example.com",
            target_user_id="user-99",
        )
        assert event.event_type == AuditEventType.ADMIN_USER_DELETED

    def test_role_assigned(self) -> None:
        event = AuditService.role_assigned(
            admin_id="admin-1",
            admin_username="admin@example.com",
            target_user_id="user-99",
            role_names=["HR", "Employee"],
        )
        assert event.event_type == AuditEventType.ADMIN_ROLE_ASSIGNED
        assert event.metadata is not None
        assert "HR" in event.metadata["role_names"]
        assert "Employee" in event.metadata["role_names"]

    def test_role_removed(self) -> None:
        event = AuditService.role_removed(
            admin_id="admin-1",
            admin_username="admin@example.com",
            target_user_id="user-99",
            role_name="HR",
        )
        assert event.event_type == AuditEventType.ADMIN_ROLE_REMOVED
        assert event.metadata is not None
        assert event.metadata["role_name"] == "HR"


# ---------------------------------------------------------------------------
# Sensitive data rules
# ---------------------------------------------------------------------------

class TestSensitiveDataExclusion:
    def test_no_password_field_on_any_event(self) -> None:
        events = [
            AuditService.login_success(email="x@example.com"),
            AuditService.login_failure(email="x@example.com"),
            AuditService.logout(),
            AuditService.permission_denied(
                user_id="u", username="u", permission="p", endpoint="/x"
            ),
            AuditService.document_read(user_id="u", document_id="d"),
            AuditService.rag_query(user_id="u", query_id="q"),
        ]
        for event in events:
            serialized = str(event)
            assert "password" not in serialized.lower(), f"password leaked in {event.event_type}"
            assert "hash" not in serialized.lower() or "checksum" in serialized.lower()

    def test_metadata_does_not_include_file_contents(self) -> None:
        event = AuditService.document_created(
            user_id="u", document_id="d", filename="doc.pdf"
        )
        assert event.metadata is not None
        assert "content" not in event.metadata
        assert "bytes" not in event.metadata
