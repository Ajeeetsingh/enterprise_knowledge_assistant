"""Integration tests for health endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_liveness() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Enterprise Knowledge Assistant" in data["app"]


def test_health_liveness_prefixed() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_endpoint() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["database"] in ("connected", "unavailable")


def test_ready_endpoint_prefixed() -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert "database" in response.json()
