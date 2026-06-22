"""Integration tests for role management API."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTHORIZATION_DENIED_MESSAGE
from app.db.models import Role, User
from tests.integration.conftest import access_token_for

ROLES_URL = "/api/v1/roles"
USERS_URL = "/api/v1/users"


def _bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user_roles_url(user_id: uuid.UUID) -> str:
    return f"{USERS_URL}/{user_id}/roles"


@pytest.fixture
def finance_role(db_session: Session) -> Role:
    role = Role(name="Finance", description="Finance team member")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def all_default_roles(
    db_session: Session,
    admin_role: Role,
    employee_role: Role,
    hr_role: Role,
    finance_role: Role,
) -> list[Role]:
    return [admin_role, employee_role, hr_role, finance_role]


def test_list_roles(
    client: TestClient,
    admin_user: User,
    all_default_roles: list[Role],
) -> None:
    token = access_token_for(admin_user)
    response = client.get(ROLES_URL, headers=_bearer_headers(token))

    assert response.status_code == 200
    names = {role["name"] for role in response.json()["roles"]}
    assert names == {"Admin", "Employee", "Finance", "HR"}


def test_assign_role(
    client: TestClient,
    admin_user: User,
    active_user: User,
    hr_role: Role,
) -> None:
    token = access_token_for(admin_user)
    response = client.post(
        _user_roles_url(active_user.id),
        headers=_bearer_headers(token),
        json={"roles": ["HR"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(active_user.id)
    assert "HR" in data["roles"]
    assert "Employee" in data["roles"]


def test_remove_role(
    client: TestClient,
    admin_user: User,
    active_user: User,
    hr_role: Role,
) -> None:
    token = access_token_for(admin_user)
    assign_response = client.post(
        _user_roles_url(active_user.id),
        headers=_bearer_headers(token),
        json={"roles": ["HR"]},
    )
    assert "HR" in assign_response.json()["roles"]

    response = client.delete(
        f"{_user_roles_url(active_user.id)}/HR",
        headers=_bearer_headers(token),
    )

    assert response.status_code == 200
    assert "HR" not in response.json()["roles"]
    assert "Employee" in response.json()["roles"]


def test_duplicate_role_assignment(
    client: TestClient,
    admin_user: User,
    active_user: User,
) -> None:
    token = access_token_for(admin_user)
    first = client.post(
        _user_roles_url(active_user.id),
        headers=_bearer_headers(token),
        json={"roles": ["Employee"]},
    )
    second = client.post(
        _user_roles_url(active_user.id),
        headers=_bearer_headers(token),
        json={"roles": ["Employee"]},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["roles"].count("Employee") == 1
    assert second.json()["roles"].count("Employee") == 1


def test_unknown_role(
    client: TestClient,
    admin_user: User,
    active_user: User,
) -> None:
    token = access_token_for(admin_user)
    response = client.post(
        _user_roles_url(active_user.id),
        headers=_bearer_headers(token),
        json={"roles": ["UnknownRole"]},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Role 'UnknownRole' not found."


def test_unknown_user(client: TestClient, admin_user: User) -> None:
    token = access_token_for(admin_user)
    missing_id = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    response = client.get(
        _user_roles_url(missing_id),
        headers=_bearer_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


def test_non_admin_forbidden(
    client: TestClient,
    active_user: User,
    all_default_roles: list[Role],
) -> None:
    token = access_token_for(active_user)
    response = client.get(ROLES_URL, headers=_bearer_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


def test_multiple_role_assignment(
    client: TestClient,
    admin_user: User,
    active_user: User,
    hr_role: Role,
    finance_role: Role,
) -> None:
    token = access_token_for(admin_user)
    response = client.post(
        _user_roles_url(active_user.id),
        headers=_bearer_headers(token),
        json={"roles": ["HR", "Finance"]},
    )

    assert response.status_code == 200
    roles = set(response.json()["roles"])
    assert {"Employee", "HR", "Finance"} <= roles
