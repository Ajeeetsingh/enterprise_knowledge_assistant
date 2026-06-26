"""Integration tests for Phase 7.7 — Monitoring & Metrics API."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Document, User
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository
from tests.integration.conftest import access_token_for, bearer_headers

MONITORING_SUMMARY_URL = "/api/v1/monitoring/summary"
MONITORING_METRICS_URL = "/api/v1/monitoring/metrics"


def _seed_monitoring_data(db_session: Session, admin_user: User) -> None:
    inactive_user = User(
        email="inactive@example.com",
        username="inactive",
        full_name="Inactive User",
        password_hash=admin_user.password_hash,
        is_active=False,
    )
    db_session.add(inactive_user)
    db_session.commit()

    document = Document(
        id=uuid.uuid4(),
        filename="policy.txt",
        content_type="text/plain",
        file_size=10,
        checksum=f"checksum-{uuid.uuid4().hex}",
        storage_path="docs/policy.txt",
        status="searchable",
        uploaded_by=admin_user.id,
        owner_id=admin_user.id,
        visibility="public",
    )
    db_session.add(document)
    db_session.commit()

    audit_repo = AuditRepository(db_session)
    audit_repo.create(
        event_type="chat.question.asked",
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=admin_user.id,
    )
    audit_repo.create(
        event_type="auth.login.failed",
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.FAILED,
    )


class TestMonitoringApi:
    def test_admin_can_get_monitoring_summary(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_monitoring_data(db_session, admin_user)
        token = access_token_for(admin_user)

        response = client.get(
            MONITORING_SUMMARY_URL,
            headers=bearer_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 2
        assert data["active_users"] == 1
        assert data["total_documents"] == 1
        assert data["total_conversations"] == 0
        assert data["questions_today"] == 1
        assert data["failed_logins_today"] == 1
        assert data["audit_events_today"] == 2

    def test_admin_can_get_system_metrics(
        self,
        client: TestClient,
        admin_user: User,
    ) -> None:
        token = access_token_for(admin_user)

        response = client.get(
            MONITORING_METRICS_URL,
            headers=bearer_headers(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["uptime_seconds"] >= 0
        assert isinstance(data["database_connected"], bool)
        assert data["version"] == "0.1.0"

    def test_employee_cannot_access_monitoring_summary(
        self,
        client: TestClient,
        active_user: User,
    ) -> None:
        token = access_token_for(active_user)

        response = client.get(
            MONITORING_SUMMARY_URL,
            headers=bearer_headers(token),
        )

        assert response.status_code == 403

    def test_unauthenticated_request_is_rejected(
        self,
        client: TestClient,
    ) -> None:
        response = client.get(MONITORING_METRICS_URL)

        assert response.status_code == 401
