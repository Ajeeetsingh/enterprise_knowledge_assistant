"""Unit tests for Phase 5.4 — Document-Level Authorization."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.auth.document_authorization import (
    AccessOutcome,
    DocumentAccessDecision,
    DocumentAuthorizationService,
    log_document_access_denied,
)
from app.auth.dependencies import get_user_system_roles
from app.auth.role_permissions import SystemRole
from app.db.models.document import Document
from app.db.models.user import User
from app.db.models.role import Role
from app.documents.visibility import DocumentVisibility
from tests.constants import TEST_PASSWORD_HASH


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_user(*role_names: str, user_id: uuid.UUID | None = None) -> User:
    user = User(
        id=user_id or uuid.uuid4(),
        email="user@example.com",
        username="testuser",
        full_name="Test User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles = [Role(name=name, description=f"{name} role") for name in role_names]
    return user


def _make_document(
    *,
    owner_id: uuid.UUID | None = None,
    visibility: DocumentVisibility = DocumentVisibility.RESTRICTED,
    allowed_roles: list[str] | None = None,
) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="policy.txt",
        content_type="text/plain",
        file_size=100,
        checksum="abc123",
        storage_path="docs/policy.txt",
        status="searchable",
        uploaded_by=uuid.uuid4(),
        owner_id=owner_id,
        visibility=visibility.value,
    )
    doc.allowed_roles = allowed_roles
    return doc


# ---------------------------------------------------------------------------
# Admin access — always granted regardless of visibility/roles
# ---------------------------------------------------------------------------

class TestAdminAccess:
    @pytest.mark.parametrize("vis", list(DocumentVisibility))
    def test_admin_can_read_any_visibility(self, vis: DocumentVisibility) -> None:
        admin = _make_user("Admin")
        doc = _make_document(visibility=vis)
        decision = DocumentAuthorizationService.can_read_document(admin, doc)
        assert decision.granted is True
        assert decision.outcome == AccessOutcome.GRANTED
        assert decision.reason == "admin"

    def test_admin_can_delete_private_document(self) -> None:
        admin = _make_user("Admin")
        doc = _make_document(visibility=DocumentVisibility.PRIVATE)
        assert DocumentAuthorizationService.can_delete_document(admin, doc).granted is True

    def test_admin_can_update_restricted_no_allowed_roles(self) -> None:
        admin = _make_user("Admin")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED, allowed_roles=[]
        )
        assert DocumentAuthorizationService.can_update_document(admin, doc).granted is True

    def test_admin_can_manage_document(self) -> None:
        admin = _make_user("Admin")
        doc = _make_document(visibility=DocumentVisibility.PRIVATE)
        assert DocumentAuthorizationService.can_manage_document(admin, doc).granted is True

    def test_admin_alias_administrator_is_recognized(self) -> None:
        user = _make_user("administrator")
        doc = _make_document(visibility=DocumentVisibility.PRIVATE)
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        # 'administrator' is an alias for Admin
        assert decision.granted is True


# ---------------------------------------------------------------------------
# Owner access
# ---------------------------------------------------------------------------

class TestOwnerAccess:
    def test_owner_can_read_own_document(self) -> None:
        user_id = uuid.uuid4()
        user = _make_user("Employee", user_id=user_id)
        doc = _make_document(
            owner_id=user_id, visibility=DocumentVisibility.PRIVATE
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is True
        assert decision.reason == "owner"

    def test_owner_can_delete_private_document(self) -> None:
        user_id = uuid.uuid4()
        user = _make_user("HR", user_id=user_id)
        doc = _make_document(
            owner_id=user_id, visibility=DocumentVisibility.PRIVATE
        )
        assert DocumentAuthorizationService.can_delete_document(user, doc).granted is True

    def test_non_owner_employee_denied_private_document(self) -> None:
        user = _make_user("Employee")
        doc = _make_document(
            owner_id=uuid.uuid4(), visibility=DocumentVisibility.PRIVATE
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False
        assert decision.outcome == AccessOutcome.DENIED_PRIVATE

    def test_no_owner_set_falls_through_to_visibility_rules(self) -> None:
        user = _make_user("Employee")
        doc = _make_document(
            owner_id=None, visibility=DocumentVisibility.PUBLIC
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is True
        assert decision.reason == "public visibility"


# ---------------------------------------------------------------------------
# PUBLIC visibility
# ---------------------------------------------------------------------------

class TestPublicVisibility:
    @pytest.mark.parametrize(
        "role_names",
        [["Employee"], ["HR"], ["Finance"], []],
    )
    def test_any_authenticated_user_can_read_public(
        self, role_names: list[str]
    ) -> None:
        user = _make_user(*role_names)
        doc = _make_document(visibility=DocumentVisibility.PUBLIC)
        assert DocumentAuthorizationService.can_read_document(user, doc).granted is True

    def test_public_document_has_granted_outcome(self) -> None:
        user = _make_user("Finance")
        doc = _make_document(visibility=DocumentVisibility.PUBLIC)
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.outcome == AccessOutcome.GRANTED
        assert decision.reason == "public visibility"


# ---------------------------------------------------------------------------
# RESTRICTED visibility
# ---------------------------------------------------------------------------

class TestRestrictedVisibility:
    def test_user_with_matching_role_is_granted(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR", "Finance"]
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is True
        assert decision.reason == "role in allowed_roles"

    def test_user_without_matching_role_is_denied(self) -> None:
        user = _make_user("Employee")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR", "Finance"]
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False
        assert decision.outcome == AccessOutcome.DENIED_ROLE

    def test_empty_allowed_roles_denies_everyone(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED, allowed_roles=[]
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False
        assert decision.outcome == AccessOutcome.DENIED_ROLE
        assert "no valid allowed roles" in decision.reason

    def test_none_allowed_roles_denies_everyone(self) -> None:
        user = _make_user("Finance")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED, allowed_roles=None
        )
        assert DocumentAuthorizationService.can_read_document(user, doc).granted is False


# ---------------------------------------------------------------------------
# PRIVATE visibility
# ---------------------------------------------------------------------------

class TestPrivateVisibility:
    def test_non_owner_always_denied(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            owner_id=uuid.uuid4(), visibility=DocumentVisibility.PRIVATE
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False
        assert decision.outcome == AccessOutcome.DENIED_PRIVATE

    def test_no_owner_non_admin_denied(self) -> None:
        user = _make_user("Finance")
        doc = _make_document(owner_id=None, visibility=DocumentVisibility.PRIVATE)
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False
        assert decision.outcome == AccessOutcome.DENIED_PRIVATE


# ---------------------------------------------------------------------------
# Unknown / malformed metadata
# ---------------------------------------------------------------------------

class TestMalformedMetadata:
    def test_unknown_visibility_denies_securely(self) -> None:
        user = _make_user("Admin")
        doc = _make_document(visibility=DocumentVisibility.PUBLIC)
        doc.visibility = "confidential"
        # Admin is checked before visibility, so still granted for admin.
        assert DocumentAuthorizationService.can_read_document(user, doc).granted is True

    def test_unknown_visibility_non_admin_denies_securely(self) -> None:
        user = _make_user("HR")
        doc = _make_document(visibility=DocumentVisibility.PUBLIC)
        doc.visibility = "top-secret"
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False
        assert decision.outcome == AccessOutcome.DENIED_UNKNOWN_VISIBILITY

    def test_unknown_role_in_allowed_roles_is_ignored(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["HR", "Confidential", "bogus"],
        )
        # "HR" is valid → granted
        assert DocumentAuthorizationService.can_read_document(user, doc).granted is True

    def test_all_unknown_roles_in_allowed_roles_denies(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=["Confidential", "bogus"],
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False

    def test_malformed_json_in_allowed_roles_denies_gracefully(self) -> None:
        user = _make_user("HR")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED,
            allowed_roles=None,
        )
        doc._allowed_roles = "{not valid json"
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False  # No exception raised

    def test_no_exception_for_any_combination(self) -> None:
        user = _make_user("Employee")
        for vis in list(DocumentVisibility) + ["unknown_vis"]:
            doc = _make_document(visibility=DocumentVisibility.PUBLIC)
            doc.visibility = vis if isinstance(vis, str) else vis.value
            try:
                DocumentAuthorizationService.can_read_document(user, doc)
            except Exception as exc:
                pytest.fail(f"Unexpected exception for visibility={vis!r}: {exc}")


# ---------------------------------------------------------------------------
# Multiple roles
# ---------------------------------------------------------------------------

class TestMultipleRoles:
    def test_multi_role_user_granted_if_any_role_matches(self) -> None:
        user = _make_user("Finance", "HR")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR"]
        )
        assert DocumentAuthorizationService.can_read_document(user, doc).granted is True

    def test_multi_role_user_denied_if_no_role_matches(self) -> None:
        user = _make_user("Finance", "Employee")
        doc = _make_document(
            visibility=DocumentVisibility.RESTRICTED, allowed_roles=["HR"]
        )
        assert DocumentAuthorizationService.can_read_document(user, doc).granted is False


# ---------------------------------------------------------------------------
# Decision fields
# ---------------------------------------------------------------------------

class TestDecisionFields:
    def test_decision_contains_document_and_user_ids(self) -> None:
        user_id = uuid.uuid4()
        user = _make_user("Employee", user_id=user_id)
        doc = _make_document(
            owner_id=None, visibility=DocumentVisibility.PUBLIC
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.document_id == doc.id
        assert decision.user_id == user_id

    def test_denied_decision_is_not_granted(self) -> None:
        user = _make_user("Employee")
        doc = _make_document(
            owner_id=uuid.uuid4(), visibility=DocumentVisibility.PRIVATE
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        assert decision.granted is False


# ---------------------------------------------------------------------------
# Logging helper
# ---------------------------------------------------------------------------

class TestLogDocumentAccessDenied:
    def test_log_does_not_raise(self) -> None:
        user_id = uuid.uuid4()
        user = _make_user("Employee", user_id=user_id)
        doc = _make_document(
            owner_id=uuid.uuid4(), visibility=DocumentVisibility.PRIVATE
        )
        decision = DocumentAuthorizationService.can_read_document(user, doc)
        # Should not raise any exception
        log_document_access_denied(
            decision=decision,
            user=user,
            endpoint="/api/v1/documents/some-id",
        )
