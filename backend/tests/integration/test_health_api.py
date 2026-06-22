"""Integration tests for health endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def health_client() -> TestClient:
    """Shared TestClient for health probes (lifespan patched in root conftest)."""
    with TestClient(app) as client:
        yield client


def test_health_liveness(health_client: TestClient) -> None:
    response = health_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ready_endpoint_when_database_available(health_client: TestClient) -> None:
    with patch("app.api.v1.health.check_database_connection", return_value=True):
        response = health_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_endpoint_when_database_unavailable(health_client: TestClient) -> None:
    with patch("app.api.v1.health.check_database_connection", return_value=False):
        response = health_client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
