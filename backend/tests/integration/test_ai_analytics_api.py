"""Integration tests for Phase 11.3 — AI Analytics API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.constants import AnalyticsEvents
from app.db.models import Conversation, Message, User
from app.db.models.enums.audit import AuditEventCategory, AuditStatus
from app.db.models.message import MessageRole
from app.db.repositories.audit_repository import AuditRepository
from tests.integration.conftest import access_token_for, bearer_headers

OVERVIEW_URL = "/api/v1/admin/analytics/ai/overview"
TRENDS_URL = "/api/v1/admin/analytics/ai/trends"
RETRIEVAL_URL = "/api/v1/admin/analytics/ai/retrieval"
QUESTIONS_URL = "/api/v1/admin/analytics/ai/questions"
FAILURES_URL = "/api/v1/admin/analytics/ai/failures"


def _seed_ai_analytics(db_session: Session, admin_user: User) -> None:
    conversation = Conversation(user_id=admin_user.id, title="HR")
    db_session.add(conversation)
    db_session.commit()

    now = datetime.now(UTC)
    db_session.add_all(
        [
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content="What is the leave policy?",
                created_at=now,
            ),
            Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content="You receive 20 days of leave.",
                citations=[{"source": "policy.txt", "excerpt": "20 days", "confidence": 0.9}],
                confidence_score=0.9,
                created_at=now + timedelta(seconds=2),
            ),
        ]
    )
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
        event_type=AnalyticsEvents.CHAT_RESPONSE,
        event_category=AuditEventCategory.CHAT,
        action="generate_answer",
        status=AuditStatus.SUCCESS,
        user_id=admin_user.id,
        metadata={"citation_count": 1, "confidence_score": 0.9},
    )
    audit_repo.create(
        event_type=AnalyticsEvents.CHAT_FAILURE,
        event_category=AuditEventCategory.CHAT,
        action="retrieve",
        status=AuditStatus.FAILED,
        user_id=admin_user.id,
        metadata={"reason": "No documents matched"},
    )


class TestAIAnalyticsApi:
    def test_admin_can_get_ai_overview(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_ai_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        response = client.get(
            OVERVIEW_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] == 1
        assert data["responses_generated"] == 1
        assert data["average_response_time_seconds"] == pytest.approx(2.0)
        assert data["retrieval_failure_rate"] == pytest.approx(50.0)

    def test_admin_can_get_ai_trends_and_quality_endpoints(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_ai_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        trends = client.get(
            TRENDS_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )
        retrieval = client.get(
            RETRIEVAL_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )
        questions = client.get(
            QUESTIONS_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )
        failures = client.get(
            FAILURES_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )

        assert trends.status_code == 200
        assert retrieval.status_code == 200
        assert questions.status_code == 200
        assert failures.status_code == 200
        assert questions.json()["items"][0]["question"] == "What is the leave policy?"
        assert failures.json()["items"][0]["reason"] == "No documents matched"

    def test_employee_cannot_access_ai_analytics(
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
