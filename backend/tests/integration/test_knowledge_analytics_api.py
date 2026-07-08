"""Integration tests for Phase 11.4 — Knowledge Analytics API."""

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

OVERVIEW_URL = "/api/v1/admin/analytics/knowledge/overview"
DOCUMENTS_URL = "/api/v1/admin/analytics/knowledge/documents"
COLLECTIONS_URL = "/api/v1/admin/analytics/knowledge/collections"
SEARCHES_URL = "/api/v1/admin/analytics/knowledge/searches"
GAPS_URL = "/api/v1/admin/analytics/knowledge/gaps"
FRESHNESS_URL = "/api/v1/admin/analytics/knowledge/freshness"


def _seed_knowledge_analytics(db_session: Session, admin_user: User) -> None:
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
        department="HR",
        visibility="public",
    )
    db_session.add(document)

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
        metadata={"citation_count": 1},
    )


class TestKnowledgeAnalyticsApi:
    def test_admin_can_get_knowledge_overview(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_knowledge_analytics(db_session, admin_user)
        token = access_token_for(admin_user)

        response = client.get(
            OVERVIEW_URL,
            headers=bearer_headers(token),
            params={"range_preset": "last_7_days"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 1
        assert data["active_documents"] == 1
        assert data["average_citations_per_document"] == pytest.approx(1.0)

    def test_admin_can_get_knowledge_detail_endpoints(
        self,
        client: TestClient,
        admin_user: User,
        db_session: Session,
    ) -> None:
        _seed_knowledge_analytics(db_session, admin_user)
        token = access_token_for(admin_user)
        headers = bearer_headers(token)
        params = {"range_preset": "last_7_days"}

        documents = client.get(DOCUMENTS_URL, headers=headers, params=params)
        collections = client.get(COLLECTIONS_URL, headers=headers, params=params)
        searches = client.get(SEARCHES_URL, headers=headers, params=params)
        gaps = client.get(GAPS_URL, headers=headers, params=params)
        freshness = client.get(FRESHNESS_URL, headers=headers, params=params)

        assert documents.status_code == 200
        assert collections.status_code == 200
        assert searches.status_code == 200
        assert gaps.status_code == 200
        assert freshness.status_code == 200
        assert documents.json()["most_viewed"][0]["filename"] == "policy.txt"
        assert searches.json()["topics"][0]["topic"] == "What is the leave policy?"
        assert freshness.json()["total_recent_uploads"] == 1

    def test_employee_cannot_access_knowledge_analytics(
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
