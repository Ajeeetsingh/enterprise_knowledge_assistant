"""Integration tests for Phase 11.6 — Error Analytics API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.db.models import User
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository
from tests.integration.conftest import access_token_for, bearer_headers

OVERVIEW_URL = "/api/v1/admin/analytics/errors/overview"
TRENDS_URL = "/api/v1/admin/analytics/errors/trends"
CATEGORIES_URL = "/api/v1/admin/analytics/errors/categories"
ENDPOINTS_URL = "/api/v1/admin/analytics/errors/endpoints"
FAILURES_URL = "/api/v1/admin/analytics/errors/failures"


def _seed_error_analytics(db_session: Session, admin_user: User) -> None:
    audit_repo = AuditRepository(db_session)
    audit_repo.create(
        event_type=AnalyticsEvents.LOGIN_FAILED,
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.FAILED,
    )
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_FAILURE,
        event_category=AuditEventCategory.CHAT,
        action="retrieve",
        status=AuditStatus.FAILED,
        user_id=admin_user.id,
        metadata={"reason": "No documents matched"},
    )
    audit_repo.create(
        event_type=AnalyticsEvents.SECURITY_PERMISSION_DENIED,
        event_category=AuditEventCategory.SECURITY,
        action="permission_check",
        status=AuditStatus.FAILED,
        user_id=admin_user.id,
        metadata={"resource": "/api/v1/chat", "required_permission": "chat"},
    )
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_QUESTION,
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=admin_user.id,
    )


class TestErrorAnalyticsApi:
    def test_admin_can_get_error_overview(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_error_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        response = client.get(
            OVERVIEW_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_errors"] == 3
        assert data["authentication_failures"] == 1
        assert data["retrieval_failures"] == 1
        assert data["api_errors"] is None

    def test_admin_can_get_error_detail_endpoints(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_error_analytics(db_session, admin_user)
        token = access_token_for(admin_user)
        headers = bearer_headers(token)
        params = {"range_preset": "last_7_days"}

        trends = client.get(TRENDS_URL, headers=headers, params=params)
        categories = client.get(CATEGORIES_URL, headers=headers, params=params)
        endpoints = client.get(ENDPOINTS_URL, headers=headers, params=params)
        failures = client.get(FAILURES_URL, headers=headers, params=params)

        assert trends.status_code == 200
        assert categories.status_code == 200
        assert endpoints.status_code == 200
        assert failures.status_code == 200
        assert categories.json()["by_severity"] is None
        assert endpoints.json()["items"][0]["endpoint"] == "/api/v1/chat"
        assert failures.json()["retrieval_failures"][0]["label"] == "No documents matched"

    def test_employee_cannot_access_error_analytics(
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
