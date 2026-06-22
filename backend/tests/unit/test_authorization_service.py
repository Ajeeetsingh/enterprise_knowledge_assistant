"""Unit tests for Phase 5.1 permission foundation."""

from __future__ import annotations

import pytest

from app.auth.authorization_service import AuthorizationService
from app.auth.permissions import (
    ALL_PERMISSIONS,
    AUDIT_PERMISSIONS,
    DOCUMENT_PERMISSIONS,
    KNOWLEDGE_PERMISSIONS,
    PERMISSION_GROUPS,
    USER_PERMISSIONS,
    Permission,
    is_known_permission,
    resolve_permission,
)
from app.auth.role_permissions import (
    ROLE_PERMISSIONS,
    SystemRole,
    is_known_role,
    resolve_system_role,
)


class TestPermissionDefinitions:
    def test_all_required_permissions_exist(self) -> None:
        expected_values = {
            "document:create",
            "document:read",
            "document:update",
            "document:delete",
            "knowledge:query",
            "knowledge:manage",
            "user:view",
            "user:create",
            "user:update",
            "user:delete",
            "audit:view",
        }
        assert {member.value for member in Permission} == expected_values

    def test_permission_groups_cover_all_permissions(self) -> None:
        grouped = set().union(*PERMISSION_GROUPS.values())
        assert grouped == set(ALL_PERMISSIONS)

    def test_document_group_members(self) -> None:
        assert DOCUMENT_PERMISSIONS == frozenset({
            Permission.DOCUMENT_CREATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.DOCUMENT_DELETE,
        })

    def test_knowledge_group_members(self) -> None:
        assert KNOWLEDGE_PERMISSIONS == frozenset({
            Permission.KNOWLEDGE_QUERY,
            Permission.KNOWLEDGE_MANAGE,
        })

    def test_user_group_members(self) -> None:
        assert USER_PERMISSIONS == frozenset({
            Permission.USER_VIEW,
            Permission.USER_CREATE,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
        })

    def test_audit_group_members(self) -> None:
        assert AUDIT_PERMISSIONS == frozenset({Permission.AUDIT_VIEW})


class TestPermissionResolution:
    @pytest.mark.parametrize(
        "raw",
        [
            Permission.DOCUMENT_READ,
            "document:read",
            "DOCUMENT:READ",
        ],
    )
    def test_resolve_known_permission(self, raw: str | Permission) -> None:
        assert resolve_permission(raw) == Permission.DOCUMENT_READ

    @pytest.mark.parametrize(
        "raw",
        [None, "", "   ", "document:archive", 123, "not-a-permission"],
    )
    def test_resolve_unknown_or_invalid_permission(self, raw: object) -> None:
        assert resolve_permission(raw) is None
        assert is_known_permission(raw) is False

    def test_is_known_permission_for_enum(self) -> None:
        assert is_known_permission(Permission.KNOWLEDGE_QUERY) is True


class TestRoleResolution:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Admin", SystemRole.ADMIN),
            ("administrator", SystemRole.ADMIN),
            ("HR", SystemRole.HR),
            ("Finance", SystemRole.FINANCE),
            ("Employee", SystemRole.EMPLOYEE),
        ],
    )
    def test_resolve_known_roles(self, raw: str, expected: SystemRole) -> None:
        assert resolve_system_role(raw) == expected
        assert is_known_role(raw) is True

    @pytest.mark.parametrize("raw", [None, "", "   ", "Guest", "SuperAdmin"])
    def test_resolve_unknown_roles(self, raw: str | None) -> None:
        assert resolve_system_role(raw) is None
        assert is_known_role(raw) is False


class TestRolePermissionMapping:
    def test_administrator_has_every_permission(self) -> None:
        assert ROLE_PERMISSIONS[SystemRole.ADMIN] == ALL_PERMISSIONS

    def test_hr_permissions(self) -> None:
        expected = frozenset({
            Permission.DOCUMENT_CREATE,
            Permission.DOCUMENT_READ,
            Permission.DOCUMENT_UPDATE,
            Permission.KNOWLEDGE_QUERY,
        })
        assert ROLE_PERMISSIONS[SystemRole.HR] == expected

    def test_finance_permissions(self) -> None:
        expected = frozenset({
            Permission.DOCUMENT_READ,
            Permission.KNOWLEDGE_QUERY,
        })
        assert ROLE_PERMISSIONS[SystemRole.FINANCE] == expected

    def test_employee_permissions(self) -> None:
        expected = frozenset({
            Permission.DOCUMENT_READ,
            Permission.KNOWLEDGE_QUERY,
        })
        assert ROLE_PERMISSIONS[SystemRole.EMPLOYEE] == expected

    def test_each_system_role_has_mapping_entry(self) -> None:
        assert set(ROLE_PERMISSIONS) == set(SystemRole)


class TestAuthorizationService:
    def test_admin_get_permissions_returns_all(self) -> None:
        permissions = AuthorizationService.get_permissions("Admin")
        assert permissions == ALL_PERMISSIONS

    def test_hr_get_permissions(self) -> None:
        permissions = AuthorizationService.get_permissions("HR")
        assert Permission.DOCUMENT_CREATE in permissions
        assert Permission.DOCUMENT_DELETE not in permissions
        assert Permission.KNOWLEDGE_QUERY in permissions

    def test_finance_get_permissions(self) -> None:
        permissions = AuthorizationService.get_permissions("Finance")
        assert permissions == frozenset({
            Permission.DOCUMENT_READ,
            Permission.KNOWLEDGE_QUERY,
        })

    def test_employee_get_permissions(self) -> None:
        permissions = AuthorizationService.get_permissions("Employee")
        assert permissions == frozenset({
            Permission.DOCUMENT_READ,
            Permission.KNOWLEDGE_QUERY,
        })

    def test_unknown_role_returns_empty_permissions(self) -> None:
        assert AuthorizationService.get_permissions("Guest") == frozenset()
        assert AuthorizationService.get_permissions(None) == frozenset()
        assert AuthorizationService.get_permissions("") == frozenset()

    def test_has_permission_for_admin(self) -> None:
        assert AuthorizationService.has_permission("Admin", Permission.USER_DELETE)
        assert AuthorizationService.has_permission("administrator", "audit:view")

    def test_has_permission_for_hr(self) -> None:
        assert AuthorizationService.has_permission("HR", Permission.DOCUMENT_UPDATE)
        assert not AuthorizationService.has_permission("HR", Permission.DOCUMENT_DELETE)

    def test_has_permission_unknown_role(self) -> None:
        assert AuthorizationService.has_permission("Guest", Permission.DOCUMENT_READ) is False

    def test_has_permission_unknown_permission(self) -> None:
        assert AuthorizationService.has_permission("Admin", "document:archive") is False
        assert AuthorizationService.has_permission("Admin", None) is False

    def test_has_any_permission(self) -> None:
        assert AuthorizationService.has_any_permission(
            "Finance",
            [Permission.DOCUMENT_READ, Permission.DOCUMENT_CREATE],
        )
        assert not AuthorizationService.has_any_permission(
            "Finance",
            [Permission.DOCUMENT_CREATE, Permission.USER_VIEW],
        )
        assert AuthorizationService.has_any_permission("HR", None) is False

    def test_has_all_permissions(self) -> None:
        assert AuthorizationService.has_all_permissions(
            "HR",
            [Permission.DOCUMENT_READ, Permission.KNOWLEDGE_QUERY],
        )
        assert not AuthorizationService.has_all_permissions(
            "HR",
            [Permission.DOCUMENT_READ, Permission.DOCUMENT_DELETE],
        )
        assert AuthorizationService.has_all_permissions("HR", []) is True

    def test_role_alias_administrator(self) -> None:
        assert AuthorizationService.get_permissions("administrator") == ALL_PERMISSIONS

    def test_get_permissions_accepts_system_role_enum(self) -> None:
        assert AuthorizationService.get_permissions(SystemRole.HR) == ROLE_PERMISSIONS[
            SystemRole.HR
        ]
