"""Tests for last-admin lockout and runtime role permission refresh."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import user_has_permission
from app.auth.permissions import Permission
from app.db.models import Role, User
from app.services import role_service, user_service
from tests.integration.conftest import access_token_for

USERS_URL = "/api/v1/users"
ME_URL = "/api/v1/auth/me"


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_create_hr_finance_admin_roles(
    client: TestClient,
    admin_user: User,
    employee_role: Role,
    hr_role: Role,
    db_session: Session,
) -> None:
    finance = Role(name="Finance", description="Finance")
    db_session.add(finance)
    db_session.commit()

    token = access_token_for(admin_user)
    for role_name, email in [
        ("Employee", "emp@example.com"),
        ("HR", "hr2@example.com"),
        ("Finance", "fin@example.com"),
        ("Admin", "admin2@example.com"),
    ]:
        response = client.post(
            USERS_URL,
            headers=_bearer(token),
            json={
                "email": email,
                "password": "NewUserPass1!",
                "full_name": role_name,
                "role": role_name,
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["roles"] == [role_name]


def test_role_change_updates_permissions_and_me(
    client: TestClient,
    admin_user: User,
    active_user: User,
    hr_role: Role,
    db_session: Session,
) -> None:
    token = access_token_for(admin_user)

    # Employee → HR
    client.post(
        f"{USERS_URL}/{active_user.id}/roles",
        headers=_bearer(token),
        json={"roles": ["HR"]},
    )
    client.delete(
        f"{USERS_URL}/{active_user.id}/roles/Employee",
        headers=_bearer(token),
    )

    db_session.refresh(active_user)
    assert user_has_permission(active_user, Permission.DOCUMENT_CREATE) is True
    assert user_has_permission(active_user, Permission.DOCUMENT_READ) is True

    user_token = access_token_for(active_user)
    me = client.get(ME_URL, headers=_bearer(user_token))
    assert me.status_code == 200
    assert "HR" in me.json()["roles"]
    assert "Employee" not in me.json()["roles"]

    # HR → Employee
    client.post(
        f"{USERS_URL}/{active_user.id}/roles",
        headers=_bearer(token),
        json={"roles": ["Employee"]},
    )
    client.delete(
        f"{USERS_URL}/{active_user.id}/roles/HR",
        headers=_bearer(token),
    )
    db_session.expire_all()
    refreshed = user_service.get_user(db_session, active_user.id)
    assert user_has_permission(refreshed, Permission.DOCUMENT_CREATE) is False
    assert user_has_permission(refreshed, Permission.DOCUMENT_READ) is True


def test_cannot_demote_last_admin(
    client: TestClient,
    admin_user: User,
    employee_role: Role,
) -> None:
    token = access_token_for(admin_user)
    response = client.delete(
        f"{USERS_URL}/{admin_user.id}/roles/Admin",
        headers=_bearer(token),
    )
    assert response.status_code == 400
    assert "last administrative" in response.json()["detail"].lower()


def test_cannot_disable_last_admin(
    client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    response = client.delete(
        f"{USERS_URL}/{admin_user.id}",
        headers=_bearer(token),
    )
    assert response.status_code == 400
    assert "last administrative" in response.json()["detail"].lower()


def test_can_demote_admin_when_another_admin_exists(
    client: TestClient,
    admin_user: User,
    admin_role: Role,
    employee_role: Role,
    db_session: Session,
) -> None:
    other = User(
        email="admin2@example.com",
        username="admin2",
        full_name="Admin Two",
        password_hash=admin_user.password_hash,
        is_active=True,
    )
    other.roles.append(admin_role)
    db_session.add(other)
    db_session.commit()

    token = access_token_for(admin_user)
    response = client.delete(
        f"{USERS_URL}/{other.id}/roles/Admin",
        headers=_bearer(token),
    )
    assert response.status_code == 200
    assert "Admin" not in response.json()["roles"]


def test_replace_user_roles_atomic(
    db_session: Session,
    active_user: User,
    hr_role: Role,
) -> None:
    roles = role_service.replace_user_roles(db_session, active_user.id, ["HR"])
    assert [role.name for role in roles] == ["HR"]
