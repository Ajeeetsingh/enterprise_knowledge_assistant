"""Unit tests for Phase 5.3 authorization dependencies."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth.dependencies import (
    AUTHORIZATION_DENIED_MESSAGE,
    get_user_permissions,
    get_user_system_roles,
    normalize_allowed_roles,
    normalize_role_names,
    require_all_permissions,
    require_any_role,
    require_permission,
    require_role,
    user_has_all_permissions,
    user_has_any_permission,
    user_has_any_role,
    user_has_permission,
    user_has_role,
)
from app.auth.permissions import Permission
from app.auth.role_permissions import SystemRole
from app.auth.security import get_current_user
from app.db.models import Role, User
from tests.constants import TEST_PASSWORD_HASH


def _make_user(*role_names: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        username="testuser",
        full_name="Test User",
        password_hash=TEST_PASSWORD_HASH,
        is_active=True,
    )
    user.roles = [Role(name=name, description=f"{name} role") for name in role_names]
    return user


class TestNormalizeRoleNames:
    def test_canonical_roles_are_preserved(self) -> None:
        result = normalize_role_names(["Admin", "HR"])
        assert result == frozenset({SystemRole.ADMIN, SystemRole.HR})

    def test_aliases_resolve_to_canonical_values(self) -> None:
        result = normalize_role_names(["administrator", "hr", "finance"])
        assert result == frozenset({
            SystemRole.ADMIN,
            SystemRole.HR,
            SystemRole.FINANCE,
        })

    def test_unknown_roles_are_ignored(self) -> None:
        result = normalize_role_names(["Admin", "Confidential", "", "  "])
        assert result == frozenset({SystemRole.ADMIN})

    def test_duplicates_are_removed(self) -> None:
        result = normalize_role_names(["Admin", "administrator", "Admin"])
        assert result == frozenset({SystemRole.ADMIN})

    def test_none_input_returns_empty_set(self) -> None:
        assert normalize_role_names(None) == frozenset()

    def test_unsupported_types_are_ignored(self) -> None:
        assert normalize_role_names([None, 42, "HR"]) == frozenset({SystemRole.HR})


class TestNormalizeAllowedRoles:
    def test_filters_unknown_document_roles(self) -> None:
        result = normalize_allowed_roles(["Admin", "bogus", "HR"])
        assert result == frozenset({SystemRole.ADMIN, SystemRole.HR})

    def test_none_returns_empty_set(self) -> None:
        assert normalize_allowed_roles(None) == frozenset()

    def test_empty_list_returns_empty_set(self) -> None:
        assert normalize_allowed_roles([]) == frozenset()


class TestUserPermissionHelpers:
    def test_admin_has_document_create(self) -> None:
        user = _make_user("Admin")
        assert user_has_permission(user, Permission.DOCUMENT_CREATE) is True

    def test_hr_has_document_create_but_not_delete(self) -> None:
        user = _make_user("HR")
        assert user_has_permission(user, Permission.DOCUMENT_CREATE) is True
        assert user_has_permission(user, Permission.DOCUMENT_DELETE) is False

    def test_employee_has_read_only(self) -> None:
        user = _make_user("Employee")
        assert user_has_permission(user, Permission.DOCUMENT_READ) is True
        assert user_has_permission(user, Permission.DOCUMENT_CREATE) is False

    def test_unknown_permission_returns_false(self) -> None:
        user = _make_user("Admin")
        assert user_has_permission(user, "document:archive") is False

    def test_user_without_roles_has_no_permissions(self) -> None:
        user = _make_user()
        assert user_has_permission(user, Permission.DOCUMENT_READ) is False
        assert get_user_permissions(user) == frozenset()

    def test_user_with_unknown_role_name_has_no_permissions(self) -> None:
        user = _make_user("Guest")
        assert get_user_system_roles(user) == frozenset()
        assert user_has_permission(user, Permission.DOCUMENT_READ) is False

    def test_user_has_any_permission(self) -> None:
        user = _make_user("Finance")
        assert user_has_any_permission(
            user,
            [Permission.DOCUMENT_CREATE, Permission.KNOWLEDGE_QUERY],
        ) is True
        assert user_has_any_permission(
            user,
            [Permission.DOCUMENT_CREATE, Permission.USER_VIEW],
        ) is False

    def test_user_has_all_permissions(self) -> None:
        user = _make_user("HR")
        assert user_has_all_permissions(
            user,
            [Permission.DOCUMENT_READ, Permission.DOCUMENT_CREATE],
        ) is True
        assert user_has_all_permissions(
            user,
            [Permission.DOCUMENT_READ, Permission.USER_VIEW],
        ) is False

    def test_user_has_all_permissions_empty_list_is_true(self) -> None:
        user = _make_user("Employee")
        assert user_has_all_permissions(user, []) is True


class TestUserRoleHelpers:
    def test_user_has_role_with_alias(self) -> None:
        user = _make_user("Admin")
        assert user_has_role(user, "administrator") is True

    def test_user_has_any_role(self) -> None:
        user = _make_user("HR")
        assert user_has_any_role(user, ["Admin", "HR"]) is True
        assert user_has_any_role(user, ["Admin", "Finance"]) is False

    def test_user_has_any_role_unknown_targets_returns_false(self) -> None:
        user = _make_user("Admin")
        assert user_has_any_role(user, ["Guest"]) is False

    def test_multi_role_user_unions_permissions(self) -> None:
        user = _make_user("HR", "Finance")
        permissions = get_user_permissions(user)
        assert Permission.DOCUMENT_CREATE in permissions
        assert Permission.KNOWLEDGE_QUERY in permissions


class TestRequirePermissionDependency:
    @pytest.fixture
    def permission_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/protected")
        def protected_endpoint(
            current_user: User = Depends(require_permission(Permission.DOCUMENT_CREATE)),
        ) -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_authorized_user_is_granted(
        self,
        permission_app: FastAPI,
    ) -> None:
        hr_user = _make_user("HR")
        permission_app.dependency_overrides[get_current_user] = lambda: hr_user
        client = TestClient(permission_app)

        response = client.get("/protected")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        permission_app.dependency_overrides.clear()

    def test_unauthorized_user_receives_403(
        self,
        permission_app: FastAPI,
    ) -> None:
        employee = _make_user("Employee")
        permission_app.dependency_overrides[get_current_user] = lambda: employee
        client = TestClient(permission_app)

        response = client.get("/protected")

        assert response.status_code == 403
        assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE
        permission_app.dependency_overrides.clear()


class TestRequireRoleDependency:
    @pytest.fixture
    def role_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/admin-only")
        def admin_endpoint(
            current_user: User = Depends(require_role("Admin")),
        ) -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_matching_role_is_granted(self, role_app: FastAPI) -> None:
        admin = _make_user("Admin")
        role_app.dependency_overrides[get_current_user] = lambda: admin
        client = TestClient(role_app)

        response = client.get("/admin-only")

        assert response.status_code == 200
        role_app.dependency_overrides.clear()

    def test_unknown_role_assignment_returns_403(self, role_app: FastAPI) -> None:
        user = _make_user("Guest")
        role_app.dependency_overrides[get_current_user] = lambda: user
        client = TestClient(role_app)

        response = client.get("/admin-only")

        assert response.status_code == 403
        assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE
        role_app.dependency_overrides.clear()


class TestRequireAnyRoleDependency:
    @pytest.fixture
    def any_role_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/hr-or-admin")
        def hr_or_admin_endpoint(
            current_user: User = Depends(require_any_role(["Admin", "HR"])),
        ) -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_any_matching_role_is_granted(self, any_role_app: FastAPI) -> None:
        hr_user = _make_user("HR")
        any_role_app.dependency_overrides[get_current_user] = lambda: hr_user
        client = TestClient(any_role_app)

        response = client.get("/hr-or-admin")

        assert response.status_code == 200
        any_role_app.dependency_overrides.clear()

    def test_no_matching_role_returns_403(self, any_role_app: FastAPI) -> None:
        employee = _make_user("Employee")
        any_role_app.dependency_overrides[get_current_user] = lambda: employee
        client = TestClient(any_role_app)

        response = client.get("/hr-or-admin")

        assert response.status_code == 403
        assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE
        any_role_app.dependency_overrides.clear()


class TestRequireAllPermissionsDependency:
    @pytest.fixture
    def all_permissions_app(self) -> FastAPI:
        app = FastAPI()

        @app.get("/needs-read-and-create")
        def endpoint(
            current_user: User = Depends(
                require_all_permissions([
                    Permission.DOCUMENT_READ,
                    Permission.DOCUMENT_CREATE,
                ])
            ),
        ) -> dict[str, str]:
            return {"status": "ok"}

        return app

    def test_user_with_all_permissions_is_granted(
        self,
        all_permissions_app: FastAPI,
    ) -> None:
        hr_user = _make_user("HR")
        all_permissions_app.dependency_overrides[get_current_user] = lambda: hr_user
        client = TestClient(all_permissions_app)

        response = client.get("/needs-read-and-create")

        assert response.status_code == 200
        all_permissions_app.dependency_overrides.clear()

    def test_user_missing_one_permission_returns_403(
        self,
        all_permissions_app: FastAPI,
    ) -> None:
        employee = _make_user("Employee")
        all_permissions_app.dependency_overrides[get_current_user] = lambda: employee
        client = TestClient(all_permissions_app)

        response = client.get("/needs-read-and-create")

        assert response.status_code == 403
        assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE
        all_permissions_app.dependency_overrides.clear()


class TestAuthorizationServiceIntegration:
    def test_permission_check_delegates_to_authorization_service(self) -> None:
        user = _make_user("Finance")
        assert user_has_permission(user, Permission.KNOWLEDGE_QUERY) is True
        assert user_has_permission(user, Permission.USER_CREATE) is False

    def test_role_normalization_before_permission_check(self) -> None:
        user = _make_user("administrator")
        assert get_user_system_roles(user) == frozenset({SystemRole.ADMIN})
        assert user_has_permission(user, Permission.USER_DELETE) is True
