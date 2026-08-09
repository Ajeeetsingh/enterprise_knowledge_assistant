"""Integration tests for Knowledge Domains API (Phase 1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTHORIZATION_DENIED_MESSAGE
from app.db.models import User
from app.db.repositories.knowledge_domain_repository import KnowledgeDomainRepository
from app.services.knowledge_domain_service import KnowledgeDomainService
from tests.integration.conftest import access_token_for

DOMAINS_URL = "/api/v1/knowledge-domains"


def _bearer_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_domains(db_session: Session) -> None:
    KnowledgeDomainService(
        KnowledgeDomainRepository(db_session)
    ).ensure_default_domains()


def test_list_knowledge_domains_sorted(
    client: TestClient,
    admin_user: User,
    seeded_domains: None,
) -> None:
    token = access_token_for(admin_user)
    response = client.get(DOMAINS_URL, headers=_bearer_headers(token))

    assert response.status_code == 200
    items = response.json()["items"]
    names = [item["name"] for item in items]
    assert names == sorted(names)
    assert "Finance" in names
    assert all(set(item.keys()) == {"id", "name", "description"} for item in items)


def test_list_requires_auth(client: TestClient) -> None:
    response = client.get(DOMAINS_URL)
    assert response.status_code == 401


def test_create_knowledge_domain(
    client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    response = client.post(
        DOMAINS_URL,
        headers=_bearer_headers(token),
        json={"name": "  Procurement ", "description": " Vendors "},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Procurement"
    assert body["description"] == "Vendors"
    assert body["id"]


def test_create_duplicate_case_insensitive(
    client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    first = client.post(
        DOMAINS_URL,
        headers=_bearer_headers(token),
        json={"name": "Legal Ops"},
    )
    assert first.status_code == 201

    second = client.post(
        DOMAINS_URL,
        headers=_bearer_headers(token),
        json={"name": "legal ops"},
    )
    assert second.status_code == 409


def test_create_empty_name_rejected(
    client: TestClient,
    admin_user: User,
) -> None:
    token = access_token_for(admin_user)
    response = client.post(
        DOMAINS_URL,
        headers=_bearer_headers(token),
        json={"name": "   "},
    )
    assert response.status_code == 422


def test_create_forbidden_for_employee(
    client: TestClient,
    active_user: User,
) -> None:
    token = access_token_for(active_user)
    response = client.post(
        DOMAINS_URL,
        headers=_bearer_headers(token),
        json={"name": "Should Fail"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == AUTHORIZATION_DENIED_MESSAGE


def test_employee_can_list(
    client: TestClient,
    active_user: User,
    seeded_domains: None,
) -> None:
    token = access_token_for(active_user)
    response = client.get(DOMAINS_URL, headers=_bearer_headers(token))
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1
