"""Integration tests for Phase 11.2 — User Analytics API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.db.models import User
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.repositories.audit_repository import AuditRepository
from tests.integration.conftest import access_token_for, bearer_headers

OVERVIEW_URL = "/api/v1/admin/analytics/users/overview"
TRENDS_URL = "/api/v1/admin/analytics/users/trends"
ACTIVITY_URL = "/api/v1/admin/analytics/users/activity"
TOP_USERS_URL = "/api/v1/admin/analytics/users/top-users"
INACTIVE_URL = "/api/v1/admin/analytics/users/inactive"


def _seed_user_analytics(db_session: Session, admin_user: User) -> None:
    quiet_user = User(
        email="quiet@example.com",
        username="quiet",
        full_name="Quiet User",
        password_hash=admin_user.password_hash,
        is_active=True,
    )
    db_session.add(quiet_user)
    db_session.commit()

    audit_repo = AuditRepository(db_session)
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_QUESTION,
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=admin_user.id,
    )
    audit_repo.create(
        event_type=AnalyticsEvents.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTH,
        action="login",
        status=AuditStatus.SUCCESS,
        user_id=admin_user.id,
    )


class TestUserAnalyticsApi:
    def test_admin_can_get_user_analytics_overview(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_user_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        response = client.get(
            OVERVIEW_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_users"] == 2
        assert data["new_users"] == 2
        assert data["daily_active_users"] == 1
        assert data["weekly_active_users"] == 1
        assert data["monthly_active_users"] == 1
        assert data["average_questions_per_user"] == 1.0

    def test_admin_can_get_user_growth_trends(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_user_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        response = client.get(
            TRENDS_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )

        assert response.status_code == 200
        data = response.json()
        assert sum(data["login_activity"]["points"].values()) == 1
        assert sum(data["questions_asked"]["points"].values()) == 1

    def test_admin_can_get_activity_and_user_lists(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_user_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        activity = client.get(
            ACTIVITY_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )
        top_users = client.get(
            TOP_USERS_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )
        inactive = client.get(
            INACTIVE_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )

        assert activity.status_code == 200
        assert top_users.status_code == 200
        assert inactive.status_code == 200
        assert top_users.json()["total"] == 1
        assert top_users.json()["items"][0]["email"] == admin_user.email
        assert inactive.json()["total"] == 1
        assert inactive.json()["items"][0]["email"] == "quiet@example.com"

    def test_employee_cannot_access_user_analytics(
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

    def test_invalid_custom_range_requires_both_dates(
        self,
        client: TestClient,
        admin_user: User,
    ) -> None:
        token = access_token_for(admin_user)

        response = client.get(
            OVERVIEW_URL,
            headers=bearer_headers(token),
            params={"range_preset": "custom"},
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "preset",
        ["today", "last_7_days", "last_30_days", "last_90_days"],
    )
    def test_date_range_presets_are_supported(
        self,
        client: TestClient,
        admin_user: User,
        preset: str,
    ) -> None:
        token = access_token_for(admin_user)

        response = client.get(
            OVERVIEW_URL,
            headers=bearer_headers(token),
            params={"range_preset": preset},
        )

        assert response.status_code == 200
