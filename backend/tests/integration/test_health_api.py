"""Integration tests for health endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_liveness() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ready_endpoint_when_database_available() -> None:
    with patch("app.api.v1.health.check_database_connection", return_value=True):
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_endpoint_when_database_unavailable() -> None:
    with patch("app.api.v1.health.check_database_connection", return_value=False):
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
