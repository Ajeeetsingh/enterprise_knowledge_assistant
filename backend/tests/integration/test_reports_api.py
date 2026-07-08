"""Integration tests for Phase 11.7 — Reporting & Export API."""

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

EXPORT_URL = "/api/v1/admin/reports/export"
FORMATS_URL = "/api/v1/admin/reports/formats"
MODULES_URL = "/api/v1/admin/reports/modules"


def _seed_user_analytics(db_session: Session, admin_user: User) -> None:
    audit_repo = AuditRepository(db_session)
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_QUESTION,
        event_category=AuditEventCategory.CHAT,
        action="ask_question",
        status=AuditStatus.SUCCESS,
        user_id=admin_user.id,
    )


class TestReportsApi:
    def test_admin_can_list_report_modules(
        self,
        client: TestClient,
        admin_user: User,
    ) -> None:
        token = access_token_for(admin_user)

        response = client.get(MODULES_URL, headers=bearer_headers(token))

        assert response.status_code == 200
        module_ids = {item["id"] for item in response.json()["items"]}
        assert module_ids == {"user", "ai", "knowledge", "monitoring", "errors"}

    def test_admin_can_list_report_formats(
        self,
        client: TestClient,
        admin_user: User,
    ) -> None:
        token = access_token_for(admin_user)

        response = client.get(FORMATS_URL, headers=bearer_headers(token))

        assert response.status_code == 200
        format_ids = {item["id"] for item in response.json()["items"]}
        assert format_ids == {"csv", "xlsx", "pdf"}

    @pytest.mark.parametrize("report_format", ["csv", "xlsx", "pdf"])
    def test_admin_can_export_user_report(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
        report_format: str,
    ) -> None:
        _seed_user_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        response = client.post(
            EXPORT_URL,
            headers=bearer_headers(token),
            json={
                "module": "user",
                "format": report_format,
                "date_range": "last_7_days",
            },
        )

        assert response.status_code == 200
        assert response.content
        disposition = response.headers.get("content-disposition", "")
        assert f"user_analytics_" in disposition
        assert disposition.endswith(f'.{report_format}"')

        if report_format == "csv":
            assert "User Analytics" in response.text
        elif report_format == "xlsx":
            assert response.content.startswith(b"PK")
        else:
            assert response.content.startswith(b"%PDF")

    def test_non_admin_cannot_export_reports(
        self,
        client: TestClient,
        active_user: User,
    ) -> None:
        token = access_token_for(active_user)

        response = client.post(
            EXPORT_URL,
            headers=bearer_headers(token),
            json={
                "module": "user",
                "format": "csv",
                "date_range": "last_7_days",
            },
        )

        assert response.status_code == 403

    def test_export_rejects_invalid_module(
        self,
        client: TestClient,
        admin_user: User,
    ) -> None:
        token = access_token_for(admin_user)

        response = client.post(
            EXPORT_URL,
            headers=bearer_headers(token),
            json={
                "module": "unknown",
                "format": "csv",
                "date_range": "last_7_days",
            },
        )

        assert response.status_code == 422

    def test_export_rejects_invalid_date_range(
        self,
        client: TestClient,
        admin_user: User,
    ) -> None:
        token = access_token_for(admin_user)

        response = client.post(
            EXPORT_URL,
            headers=bearer_headers(token),
            json={
                "module": "user",
                "format": "csv",
                "date_range": "custom",
                "start_date": datetime(2026, 6, 24, tzinfo=UTC).isoformat(),
                "end_date": datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
            },
        )

        assert response.status_code == 422

    def test_unauthenticated_export_is_rejected(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            EXPORT_URL,
            json={
                "module": "user",
                "format": "csv",
                "date_range": "last_7_days",
            },
        )

        assert response.status_code == 401
