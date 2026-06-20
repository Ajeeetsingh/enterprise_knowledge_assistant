"""Integration tests for RBAC authorization dependencies."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.models import User
from tests.integration.conftest import access_token_for

ADMIN_DEMO_URL = "/api/v1/auth/admin-demo"
HR_DEMO_URL = "/api/v1/auth/hr-demo"
SUPERUSER_DEMO_URL = "/api/v1/auth/superuser-demo"


def _bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_access_granted(client: TestClient, admin_user: User) -> None:
    token = access_token_for(admin_user)
    response = client.get(ADMIN_DEMO_URL, headers=_bearer_headers(token))

    assert response.status_code == 200
    assert response.json()["message"] == "Admin access granted."


def test_hr_access_granted(client: TestClient, hr_user: User) -> None:
    token = access_token_for(hr_user)
    response = client.get(HR_DEMO_URL, headers=_bearer_headers(token))

    assert response.status_code == 200
    assert response.json()["message"] == "HR or Admin access granted."


def test_multiple_role_authorization_admin_on_hr_demo(
    client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    response = client.get(HR_DEMO_URL, headers=_bearer_headers(token))

    assert response.status_code == 200


def test_employee_denied_admin_demo(client: TestClient, active_user: User) -> None:
    token = access_token_for(active_user)
    response = client.get(ADMIN_DEMO_URL, headers=_bearer_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions."


def test_employee_denied_hr_demo(client: TestClient, active_user: User) -> None:
    token = access_token_for(active_user)
    response = client.get(HR_DEMO_URL, headers=_bearer_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions."


def test_missing_token(client: TestClient) -> None:
    response = client.get(ADMIN_DEMO_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."


def test_invalid_token(client: TestClient) -> None:
    response = client.get(ADMIN_DEMO_URL, headers=_bearer_headers("invalid-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials."


def test_superuser_access(client: TestClient, superuser: User) -> None:
    token = access_token_for(superuser)
    response = client.get(SUPERUSER_DEMO_URL, headers=_bearer_headers(token))

    assert response.status_code == 200
    assert response.json()["message"] == "Superuser access granted."


def test_non_superuser_rejection(client: TestClient, admin_user: User) -> None:
    token = access_token_for(admin_user)
    response = client.get(SUPERUSER_DEMO_URL, headers=_bearer_headers(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions."
