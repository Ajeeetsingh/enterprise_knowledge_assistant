"""Shared helpers for conversation-aware chat integration tests."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Document, User
from app.db.models.document import Document as DocumentModel
from app.documents.visibility import DocumentVisibility
from app.query_router import QueryRouter
from app.query_router.knowledge_classifier import KnowledgeRouteClassifier, KnowledgeRouteResult
from app.query_router.types import QueryRoute
from tests.integration.conftest import bearer_headers

CONVERSATIONS_URL = "/api/v1/conversations"
ASK_URL = "/api/v1/chat/ask"


def create_conversation(
    client: TestClient,
    token: str,
    *,
    title: str = "Test Conversation",
) -> str:
    """Create a conversation and return its ID."""
    response = client.post(
        CONVERSATIONS_URL,
        headers=bearer_headers(token),
        json={"title": title},
    )
    assert response.status_code == 201
    return response.json()["id"]


def ask_payload(conversation_id: str, question: str) -> dict[str, str]:
    """Build a conversation-aware chat request body."""
    return {
        "conversation_id": conversation_id,
        "question": question,
    }


def add_public_searchable_document(
    db: Session,
    uploader: User,
    *,
    filename: str = "integration_public.txt",
) -> Document:
    """Insert a public searchable document so DOCUMENT_QUERY can reach RAG."""
    doc = DocumentModel(
        id=uuid.uuid4(),
        filename=filename,
        content_type="text/plain",
        file_size=100,
        checksum=f"csum-{filename}-{uuid.uuid4().hex[:8]}",
        storage_path=f"docs/{filename}",
        status="searchable",
        uploaded_by=uploader.id,
        owner_id=uploader.id,
        visibility=DocumentVisibility.PUBLIC.value,
    )
    doc.allowed_roles = None
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def force_document_query_router() -> QueryRouter:
    """Router that skips product-help and always classifies as DOCUMENT_QUERY."""
    matcher = MagicMock()
    matcher.match_and_answer.return_value = None
    classifier = MagicMock(spec=KnowledgeRouteClassifier)
    classifier.classify.return_value = KnowledgeRouteResult(
        QueryRoute.DOCUMENT_QUERY,
        0.95,
        "integration_force_document",
        ("test",),
    )
    return QueryRouter(
        product_matcher=matcher,
        knowledge_classifier=classifier,
        llm_provider=False,
    )
