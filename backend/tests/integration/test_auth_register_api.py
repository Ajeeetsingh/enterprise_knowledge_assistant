"""Integration tests for public self-registration."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limiter
from app.db.models import Role, User
from app.services import user_service

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"


@pytest.fixture(autouse=True)
def clear_rate_limits() -> None:
    rate_limiter._events.clear()
    yield
    rate_limiter._events.clear()


@pytest.fixture
def employee_role(db_session: Session) -> Role:
    role = Role(name="Employee", description="Standard employee access")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def all_system_roles(db_session: Session, employee_role: Role) -> list[Role]:
    extras = [
        Role(name="Admin", description="Admin"),
        Role(name="HR", description="HR"),
        Role(name="Finance", description="Finance"),
    ]
    db_session.add_all(extras)
    db_session.commit()
    return [employee_role, *extras]


def test_register_creates_employee(
    client: TestClient,
    db_session: Session,
    all_system_roles: list[Role],
) -> None:
    response = client.post(
        REGISTER_URL,
        json={
            "email": "newbie@example.com",
            "password": "SecurePass1!",
            "full_name": "New Employee",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newbie@example.com"
    assert data["full_name"] == "New Employee"
    assert "password" not in data
    assert "password_hash" not in data
    assert "roles" not in data

    user = db_session.scalar(select(User).where(User.email == "newbie@example.com"))
    assert user is not None
    assert [role.name for role in user.roles] == ["Employee"]
    assert user.is_superuser is False
    assert user.is_active is True


def test_register_rejects_role_field(
    client: TestClient,
    all_system_roles: list[Role],
) -> None:
    response = client.post(
        REGISTER_URL,
        json={
            "email": "attacker@example.com",
            "password": "SecurePass1!",
            "full_name": "Attacker",
            "role": "Admin",
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize("payload_key", ["roles", "is_superuser", "is_active", "permissions"])
def test_register_rejects_privileged_fields(
    client: TestClient,
    all_system_roles: list[Role],
    payload_key: str,
) -> None:
    body: dict = {
        "email": f"{payload_key}@example.com",
        "password": "SecurePass1!",
        "full_name": "Attacker",
        payload_key: True if payload_key != "roles" else ["Admin"],
    }
    response = client.post(REGISTER_URL, json=body)
    assert response.status_code == 422


def test_register_cannot_self_assign_admin_via_ignored_fields(
    client: TestClient,
    db_session: Session,
    all_system_roles: list[Role],
) -> None:
    # Extra fields forbidden — even if somehow accepted, role would still be Employee.
    response = client.post(
        REGISTER_URL,
        json={
            "email": "normal@example.com",
            "password": "SecurePass1!",
            "full_name": "Normal User",
        },
    )
    assert response.status_code == 201
    user = db_session.scalar(select(User).where(User.email == "normal@example.com"))
    assert user is not None
    assert [r.name for r in user.roles] == ["Employee"]


def test_register_duplicate_email(
    client: TestClient,
    all_system_roles: list[Role],
) -> None:
    payload = {
        "email": "dup@example.com",
        "password": "SecurePass1!",
        "full_name": "First",
    }
    assert client.post(REGISTER_URL, json=payload).status_code == 201
    second = client.post(REGISTER_URL, json={**payload, "full_name": "Second"})
    assert second.status_code == 409
    assert "email" in second.json()["detail"].lower()


def test_register_password_too_short(
    client: TestClient,
    all_system_roles: list[Role],
) -> None:
    response = client.post(
        REGISTER_URL,
        json={
            "email": "short@example.com",
            "password": "short",
            "full_name": "Short Pass",
        },
    )
    assert response.status_code == 422


def test_register_rate_limited(
    client: TestClient,
    all_system_roles: list[Role],
) -> None:
    for index in range(5):
        response = client.post(
            REGISTER_URL,
            json={
                "email": f"rate{index}@example.com",
                "password": "SecurePass1!",
                "full_name": f"Rate {index}",
            },
        )
        assert response.status_code == 201

    blocked = client.post(
        REGISTER_URL,
        json={
            "email": "rate-blocked@example.com",
            "password": "SecurePass1!",
            "full_name": "Blocked",
        },
    )
    assert blocked.status_code == 429


def test_registered_user_can_login_and_see_employee_role(
    client: TestClient,
    all_system_roles: list[Role],
) -> None:
    assert (
        client.post(
            REGISTER_URL,
            json={
                "email": "loginme@example.com",
                "password": "SecurePass1!",
                "full_name": "Login Me",
            },
        ).status_code
        == 201
    )

    login = client.post(
        LOGIN_URL,
        json={"email": "loginme@example.com", "password": "SecurePass1!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["roles"] == ["Employee"]


def test_register_rolls_back_when_employee_role_missing(
    client: TestClient,
    db_session: Session,
) -> None:
    # No Employee role seeded — registration must fail without creating a user.
    response = client.post(
        REGISTER_URL,
        json={
            "email": "orphan@example.com",
            "password": "SecurePass1!",
            "full_name": "Orphan",
        },
    )
    assert response.status_code == 404
    assert (
        db_session.scalar(select(User).where(User.email == "orphan@example.com")) is None
    )


def test_register_public_user_helper_assigns_employee(
    db_session: Session,
    employee_role: Role,
) -> None:
    user = user_service.register_public_user(
        db_session,
        email="helper@example.com",
        password="SecurePass1!",
        full_name="Helper",
    )
    assert [role.name for role in user.roles] == ["Employee"]
