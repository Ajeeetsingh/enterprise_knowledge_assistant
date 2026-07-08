"""Integration tests for Phase 11.5 — System Monitoring Analytics API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.db.models import Conversation, Document, Message, User
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.models.message import MessageRole
from app.db.repositories.audit_repository import AuditRepository
from tests.integration.conftest import access_token_for, bearer_headers

OVERVIEW_URL = "/api/v1/admin/analytics/monitoring/overview"
PERFORMANCE_URL = "/api/v1/admin/analytics/monitoring/performance"
RESOURCES_URL = "/api/v1/admin/analytics/monitoring/resources"
SERVICES_URL = "/api/v1/admin/analytics/monitoring/services"
TRENDS_URL = "/api/v1/admin/analytics/monitoring/trends"


def _seed_monitoring_analytics(db_session: Session, admin_user: User) -> None:
    document = Document(
        id=uuid.uuid4(),
        filename="policy.txt",
        content_type="text/plain",
        file_size=256,
        checksum=f"checksum-{uuid.uuid4().hex}",
        storage_path="docs/policy.txt",
        status="searchable",
        uploaded_by=admin_user.id,
        owner_id=admin_user.id,
        visibility="public",
    )
    db_session.add(document)

    conversation = Conversation(user_id=admin_user.id, title="Ops")
    db_session.add(conversation)
    db_session.commit()

    now = datetime.now(UTC)
    db_session.add_all(
        [
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content="Health check",
                created_at=now,
            ),
            Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content="Healthy.",
                created_at=now + timedelta(seconds=2),
            ),
        ]
    )
    db_session.commit()

    audit_repo = AuditRepository(db_session)
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_RESPONSE,
        event_category=AuditEventCategory.CHAT,
        action="generate_answer",
        status=AuditStatus.SUCCESS,
        user_id=admin_user.id,
    )
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_FAILURE,
        event_category=AuditEventCategory.CHAT,
        action="retrieve",
        status=AuditStatus.FAILED,
        user_id=admin_user.id,
        metadata={"reason": "No documents matched"},
    )


class TestSystemMonitoringAnalyticsApi:
    def test_admin_can_get_monitoring_overview(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_monitoring_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        response = client.get(
            OVERVIEW_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["api_health"] == "healthy"
        assert data["database_health"] == "healthy"
        assert data["overall_system_status"] in {"healthy", "degraded", "unavailable"}

    def test_admin_can_get_monitoring_detail_endpoints(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_monitoring_analytics(db_session, admin_user)
        token = access_token_for(admin_user)
        headers = bearer_headers(token)
        params = {"range_preset": "last_7_days"}

        performance = client.get(PERFORMANCE_URL, headers=headers, params=params)
        resources = client.get(RESOURCES_URL, headers=headers, params=params)
        services = client.get(SERVICES_URL, headers=headers, params=params)
        trends = client.get(TRENDS_URL, headers=headers, params=params)

        assert performance.status_code == 200
        assert resources.status_code == 200
        assert services.status_code == 200
        assert trends.status_code == 200
        assert performance.json()["average_api_response_time_seconds"] is None
        assert performance.json()["average_search_time_seconds"] == pytest.approx(2.0)
        assert resources.json()["total_documents"] == 1
        assert resources.json()["storage_usage_bytes"] == 256
        assert resources.json()["vector_index_size_bytes"] is None
        assert len(services.json()["items"]) == 5
        assert trends.json()["timeline_total"] >= 2

    def test_employee_cannot_access_monitoring_analytics(
        self,
        client: TestClient,
        active_user: User,
    ) -> None:
        token = access_token_for(active_user)

        response = client.get(
            OVERVIEW_URL,
            headers=bearer_headers(token),
        )

        assert response.status_code == 403
